"""
ProcureFlow AI — Fraud Detection Crew
Track 2: UiPath Maestro BPMN

CrewAI multi-agent crew for detecting procurement fraud patterns:
- Duplicate invoices
- Split-purchase policy evasion
- Bank account change manipulation
- Vendor impersonation / shell companies
- Collusion indicators

Called by UiPath Maestro BPMN when invoice match score < 95 or
when risk flags are raised by the 3-way match agent.
"""

import logging
import re
from datetime import datetime
from typing import Optional

from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ProcureFlow AI — Fraud Detection",
    description="CrewAI procurement fraud detection crew",
    version="1.0.0"
)


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

class InvoiceFraudRequest(BaseModel):
    invoice_id: str
    vendor_id: str
    vendor_name: str
    vendor_bank_account: str
    invoice_amount: float
    invoice_date: str
    line_items: list[dict]
    po_number: Optional[str] = None
    requestor_id: Optional[str] = None
    approver_id: Optional[str] = None
    department: Optional[str] = None
    match_score: float = Field(default=1.0, ge=0.0, le=1.0)
    flags: list[str] = []


class FraudFinding(BaseModel):
    fraud_type: str
    severity: str  # LOW | MEDIUM | HIGH | CRITICAL
    confidence: float
    evidence: list[str]
    recommended_action: str


class FraudDetectionResult(BaseModel):
    invoice_id: str
    vendor_id: str
    overall_risk: str  # CLEAN | LOW_RISK | SUSPICIOUS | FRAUDULENT
    risk_score: int = Field(..., ge=0, le=100)
    findings: list[FraudFinding]
    approve: bool
    hold_for_review: bool
    escalate_to_audit: bool
    case_notes: str
    investigated_at: str


# ─────────────────────────────────────────────
# Fraud Detection Tools
# ─────────────────────────────────────────────

@tool("check_duplicate_invoices")
def check_duplicate_invoices(vendor_id: str, invoice_amount: float, invoice_date: str) -> str:
    """
    Check for duplicate invoice submissions from this vendor.
    Looks for same amount, similar dates, or same invoice number patterns.
    """
    logger.info(f"Checking duplicate invoices for vendor {vendor_id}")

    # Simulated duplicate invoice detection
    # In production: query invoice database with fuzzy matching
    mock_history = {
        "V-2241": [
            {"invoice_id": "INV-88821", "amount": invoice_amount, "date": "2026-05-15",
             "status": "PAID"},
        ],
        "V-9982": [],
        "V-7734": [
            {"invoice_id": "INV-44011", "amount": invoice_amount - 0.01, "date": invoice_date,
             "status": "PENDING"},
        ],
    }

    history = mock_history.get(vendor_id, [])
    if not history:
        return json_safe({"duplicate_found": False, "similar_invoices": []})

    # Check for exact or near-duplicate amounts (within 1%)
    duplicates = []
    for inv in history:
        amount_diff_pct = abs(inv["amount"] - invoice_amount) / max(invoice_amount, 0.01)
        if amount_diff_pct < 0.01:
            duplicates.append(inv)

    if duplicates:
        return json_safe({
            "duplicate_found": True,
            "similar_invoices": duplicates,
            "risk": "HIGH",
            "note": "Potential duplicate invoice — same/similar amount submitted recently"
        })

    return json_safe({"duplicate_found": False, "similar_invoices": [], "risk": "LOW"})


@tool("detect_split_purchases")
def detect_split_purchases(vendor_id: str, invoice_amount: float, requestor_id: str,
                            department: str) -> str:
    """
    Detect split purchases designed to evade approval thresholds.
    Flags when multiple invoices from same vendor/requestor are just below approval limits.
    """
    logger.info(f"Checking split purchase patterns for {requestor_id} / {vendor_id}")

    # Approval thresholds by department (mirrors requisition_agent.py)
    thresholds = {
        "IT": 10000, "MARKETING": 5000, "FACILITIES": 15000, "DEFAULT": 10000
    }
    threshold = thresholds.get(department, thresholds["DEFAULT"])

    # Simulate finding other recent invoices from same requestor/vendor
    # In production: query last 30 days of invoices
    mock_recent = {
        ("EMP-1421", "V-2241"): [
            {"amount": threshold * 0.95, "date": "2026-06-25", "invoice_id": "INV-99001"},
            {"amount": threshold * 0.93, "date": "2026-06-20", "invoice_id": "INV-98887"},
        ]
    }

    recent = mock_recent.get((requestor_id, vendor_id), [])
    if not recent:
        return json_safe({"split_detected": False})

    # If current + recent would exceed threshold → split purchase suspected
    total_recent = sum(r["amount"] for r in recent)
    if invoice_amount < threshold * 0.99 and total_recent + invoice_amount > threshold:
        return json_safe({
            "split_detected": True,
            "threshold": threshold,
            "current_invoice": invoice_amount,
            "recent_invoices_total": total_recent,
            "combined_total": total_recent + invoice_amount,
            "risk": "HIGH",
            "note": (
                f"Split purchase suspected: {len(recent)} recent invoices totaling "
                f"${total_recent:,.2f} would bring combined total to "
                f"${total_recent + invoice_amount:,.2f} (above ${threshold:,} threshold)"
            )
        })

    return json_safe({"split_detected": False, "risk": "LOW"})


@tool("verify_vendor_legitimacy")
def verify_vendor_legitimacy(vendor_id: str, vendor_name: str, vendor_bank_account: str) -> str:
    """
    Verify vendor is legitimate: check approved vendor list, registration status,
    and flag recent bank account changes (common in impersonation attacks).
    """
    logger.info(f"Verifying vendor legitimacy: {vendor_id}")

    # Simulate vendor registry check
    approved_vendors = {
        "V-1001": {"name": "Contoso Tech Ltd", "bank": "ACC-8821-UK", "status": "APPROVED",
                   "bank_last_changed": "2025-01-15"},
        "V-2241": {"name": "FabriKam Supplies", "bank": "ACC-4492-US", "status": "APPROVED",
                   "bank_last_changed": "2026-06-20"},  # Very recently changed!
        "V-9982": {"name": "Northwind Consulting", "bank": "ACC-7731-EU", "status": "APPROVED",
                   "bank_last_changed": "2024-08-01"},
    }

    vendor_record = approved_vendors.get(vendor_id)
    if not vendor_record:
        return json_safe({
            "legitimate": False,
            "risk": "CRITICAL",
            "note": f"Vendor {vendor_id} NOT FOUND in approved vendor registry"
        })

    issues = []

    # Check name mismatch
    if vendor_record["name"].lower() != vendor_name.lower():
        issues.append(f"Vendor name mismatch: registry='{vendor_record['name']}' invoice='{vendor_name}'")

    # Check bank account mismatch
    if vendor_record["bank"] != vendor_bank_account:
        issues.append(f"Bank account mismatch: registry='{vendor_record['bank']}' invoice='{vendor_bank_account}'")

    # Check recent bank account change (within 30 days — major fraud signal)
    from datetime import date
    try:
        last_changed = date.fromisoformat(vendor_record["bank_last_changed"])
        days_since_change = (date.today() - last_changed).days
        if days_since_change <= 30:
            issues.append(
                f"CRITICAL: Bank account changed {days_since_change} days ago — "
                "potential vendor impersonation / business email compromise attack"
            )
    except ValueError:
        pass

    if issues:
        return json_safe({
            "legitimate": False if any("CRITICAL" in i for i in issues) else True,
            "issues": issues,
            "risk": "CRITICAL" if any("CRITICAL" in i for i in issues) else "HIGH"
        })

    return json_safe({
        "legitimate": True,
        "vendor_record": vendor_record,
        "risk": "LOW",
        "note": "Vendor verified in approved registry with matching name and bank details"
    })


@tool("check_approver_vendor_collusion")
def check_approver_vendor_collusion(approver_id: str, vendor_id: str,
                                    invoice_amount: float) -> str:
    """
    Detect potential collusion between internal approvers and external vendors.
    Checks approval patterns, relationship disclosures, and behavioral anomalies.
    """
    logger.info(f"Checking collusion signals: approver={approver_id}, vendor={vendor_id}")

    # Simulate collusion detection logic
    # In production: graph analysis of approval patterns, HR conflict-of-interest disclosures
    high_volume_approvals = {
        ("MGR-4421", "V-2241"): {"count_90d": 47, "total_amount": 215000},
        ("MGR-8820", "V-9982"): {"count_90d": 3, "total_amount": 12000},
    }

    pattern = high_volume_approvals.get((approver_id, vendor_id))
    if pattern and pattern["count_90d"] > 20:
        return json_safe({
            "collusion_risk": "HIGH",
            "evidence": {
                "approvals_90d": pattern["count_90d"],
                "total_amount_90d": pattern["total_amount"],
                "note": (
                    f"Approver {approver_id} approved {pattern['count_90d']} invoices "
                    f"totaling ${pattern['total_amount']:,} from vendor {vendor_id} in 90 days"
                )
            },
            "recommendation": "Escalate to Internal Audit for relationship review"
        })

    return json_safe({
        "collusion_risk": "LOW",
        "note": "No unusual approval patterns detected for this approver-vendor pair"
    })


@tool("analyze_line_item_anomalies")
def analyze_line_item_anomalies(line_items: str, vendor_id: str) -> str:
    """
    Analyze invoice line items for pricing anomalies, phantom services,
    and descriptions inconsistent with vendor's registered business type.
    """
    logger.info(f"Analyzing line items for vendor {vendor_id}")

    # Parse line items (passed as JSON string by LLM)
    try:
        import json
        items = json.loads(line_items)
    except Exception:
        return json_safe({"error": "Could not parse line items", "risk": "UNKNOWN"})

    issues = []

    for item in items:
        description = item.get("description", "").lower()
        amount = item.get("amount", 0)
        quantity = item.get("quantity", 1)

        # Check for vague/suspicious descriptions (phantom services)
        vague_keywords = ["consulting services", "professional services", "misc", "other",
                          "management fees", "advisory", "general services"]
        if any(kw in description for kw in vague_keywords) and amount > 5000:
            issues.append(
                f"Vague high-value line item: '{item.get('description')}' for ${amount:,.2f} — "
                "potential phantom service billing"
            )

        # Unusually high unit price
        unit_price = amount / max(quantity, 1)
        if unit_price > 50000:
            issues.append(
                f"Unusually high unit price: ${unit_price:,.2f} for '{item.get('description')}'"
            )

    if issues:
        return json_safe({"anomalies_found": True, "issues": issues, "risk": "MEDIUM"})

    return json_safe({
        "anomalies_found": False,
        "risk": "LOW",
        "note": f"All {len(items)} line items appear legitimate"
    })


def json_safe(obj: dict) -> str:
    """Convert dict to JSON string for tool return values."""
    import json
    return json.dumps(obj, indent=2, default=str)


# ─────────────────────────────────────────────
# CrewAI Agents
# ─────────────────────────────────────────────

def create_fraud_detection_crew(invoice_data: InvoiceFraudRequest) -> str:
    """Create and run the fraud detection crew for a given invoice."""

    # Agent 1: Invoice Fraud Analyst
    fraud_analyst = Agent(
        role="Invoice Fraud Analyst",
        goal=(
            "Detect fraudulent patterns in invoice submissions including "
            "duplicates, split purchases, and billing anomalies."
        ),
        backstory=(
            "Former accounts payable forensic specialist with 15 years of "
            "experience investigating procurement fraud. Expert at identifying "
            "duplicate invoices, split-purchase schemes, and phantom billing."
        ),
        tools=[check_duplicate_invoices, detect_split_purchases, analyze_line_item_anomalies],
        verbose=True,
        allow_delegation=False,
    )

    # Agent 2: Vendor Risk Investigator
    vendor_investigator = Agent(
        role="Vendor Risk Investigator",
        goal=(
            "Verify vendor legitimacy and detect vendor impersonation attacks, "
            "business email compromise, and unauthorized bank account changes."
        ),
        backstory=(
            "Cybersecurity expert specialized in Business Email Compromise (BEC) "
            "and vendor fraud. Has prevented over $50M in fraudulent wire transfers "
            "by detecting bank account change scams before payment."
        ),
        tools=[verify_vendor_legitimacy, check_approver_vendor_collusion],
        verbose=True,
        allow_delegation=False,
    )

    # Agent 3: Compliance Adjudicator
    compliance_adjudicator = Agent(
        role="Procurement Compliance Adjudicator",
        goal=(
            "Synthesize all fraud findings into a final risk assessment and "
            "recommend whether to approve, hold, or escalate the invoice."
        ),
        backstory=(
            "CFO-level compliance officer with expertise in SOX, anti-bribery laws, "
            "and corporate procurement policy. Makes final adjudication decisions "
            "on complex fraud cases, balancing risk mitigation with business continuity."
        ),
        tools=[],
        verbose=True,
        allow_delegation=False,
    )

    # Tasks
    task1 = Task(
        description=(
            f"Investigate invoice INV-{invoice_data.invoice_id} from vendor "
            f"{invoice_data.vendor_name} (ID: {invoice_data.vendor_id}) for ${invoice_data.invoice_amount:,.2f}.\n\n"
            f"Run ALL of these checks:\n"
            f"1. check_duplicate_invoices for vendor_id={invoice_data.vendor_id}, "
            f"amount={invoice_data.invoice_amount}, date={invoice_data.invoice_date}\n"
            f"2. detect_split_purchases for vendor_id={invoice_data.vendor_id}, "
            f"amount={invoice_data.invoice_amount}, requestor_id={invoice_data.requestor_id or 'UNKNOWN'}, "
            f"department={invoice_data.department or 'DEFAULT'}\n"
            f"3. analyze_line_item_anomalies with the line items: "
            f"{str(invoice_data.line_items)}\n\n"
            "Report ALL findings with risk levels and evidence."
        ),
        agent=fraud_analyst,
        expected_output=(
            "Fraud analysis report covering duplicate detection, split purchase analysis, "
            "and line item anomalies with risk levels (LOW/MEDIUM/HIGH/CRITICAL) and evidence."
        ),
    )

    task2 = Task(
        description=(
            f"Verify vendor legitimacy for:\n"
            f"- Vendor ID: {invoice_data.vendor_id}\n"
            f"- Vendor Name: {invoice_data.vendor_name}\n"
            f"- Bank Account: {invoice_data.vendor_bank_account}\n"
            f"- Approver ID: {invoice_data.approver_id or 'N/A'}\n\n"
            "Run these checks:\n"
            f"1. verify_vendor_legitimacy with vendor_id, vendor_name, bank_account\n"
            f"2. check_approver_vendor_collusion with approver_id={invoice_data.approver_id or 'N/A'}, "
            f"vendor_id={invoice_data.vendor_id}, amount={invoice_data.invoice_amount}\n\n"
            "Flag any bank account changes, name mismatches, or collusion signals."
        ),
        agent=vendor_investigator,
        expected_output=(
            "Vendor verification report covering legitimacy check, bank account validation, "
            "and approver collusion analysis with evidence and risk assessment."
        ),
    )

    task3 = Task(
        description=(
            "Based on the fraud analysis and vendor verification reports:\n\n"
            "1. Calculate an overall risk score (0-100)\n"
            "2. Classify overall risk: CLEAN (<20), LOW_RISK (20-50), SUSPICIOUS (50-80), FRAUDULENT (>80)\n"
            "3. List all confirmed fraud findings with severity and evidence\n"
            "4. Make a final recommendation:\n"
            "   - APPROVE: risk score < 30, no HIGH/CRITICAL findings\n"
            "   - HOLD_FOR_REVIEW: risk score 30-70, needs human review\n"
            "   - ESCALATE_TO_AUDIT: risk score > 70 or any CRITICAL finding\n\n"
            "Format your final output as a structured case summary."
        ),
        agent=compliance_adjudicator,
        expected_output=(
            "Final fraud assessment with risk score, classification, consolidated findings, "
            "and clear approve/hold/escalate recommendation with detailed case notes."
        ),
    )

    crew = Crew(
        agents=[fraud_analyst, vendor_investigator, compliance_adjudicator],
        tasks=[task1, task2, task3],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    return str(result)


# ─────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────

@app.post("/detect-fraud", response_model=FraudDetectionResult)
async def detect_fraud(request: InvoiceFraudRequest):
    """
    Run the full fraud detection crew on an invoice.
    Called by UiPath Maestro BPMN when risk flags are raised.
    """
    try:
        logger.info(f"Starting fraud investigation for invoice {request.invoice_id}")

        crew_output = create_fraud_detection_crew(request)

        # Parse crew output into structured result
        # The adjudicator's output is in natural language — extract key fields
        result_text = crew_output.lower()

        # Determine risk level from crew output
        if "fraudulent" in result_text or "critical" in result_text:
            overall_risk = "FRAUDULENT"
            risk_score = 90
            approve = False
            hold = False
            escalate = True
        elif "suspicious" in result_text or "high risk" in result_text:
            overall_risk = "SUSPICIOUS"
            risk_score = 65
            approve = False
            hold = True
            escalate = False
        elif "low risk" in result_text or "low_risk" in result_text:
            overall_risk = "LOW_RISK"
            risk_score = 30
            approve = False
            hold = True
            escalate = False
        else:
            overall_risk = "CLEAN"
            risk_score = 15
            approve = True
            hold = False
            escalate = False

        # Build findings from flags
        findings = []
        if request.flags:
            for flag in request.flags:
                findings.append(FraudFinding(
                    fraud_type=flag,
                    severity="MEDIUM",
                    confidence=0.75,
                    evidence=[f"System flag raised: {flag}"],
                    recommended_action="Review by AP supervisor"
                ))

        return FraudDetectionResult(
            invoice_id=request.invoice_id,
            vendor_id=request.vendor_id,
            overall_risk=overall_risk,
            risk_score=risk_score,
            findings=findings,
            approve=approve,
            hold_for_review=hold,
            escalate_to_audit=escalate,
            case_notes=crew_output[:2000],  # Truncate for response
            investigated_at=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Fraud detection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fraud detection failed: {str(e)}")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "fraud-detection-crew", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)
