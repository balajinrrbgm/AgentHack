"""
ProcureFlow AI — LangChain Requisition Intelligence Agent
Track 2: UiPath Maestro BPMN

Parses free-text purchase requests, extracts structured procurement data,
recommends vendors, and flags policy violations.

Built with UiPath for Coding Agents (Claude Code) - bonus points!
"""

import os
import json
import logging
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_community.vectorstores import Chroma

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ProcureFlow AI — Requisition Intelligence Agent",
    description="AI-powered procurement requisition processing and vendor selection",
    version="1.0.0"
)

# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

class RequisitionRequest(BaseModel):
    requester_id: str
    department: str
    cost_center: str
    request_text: str = Field(..., description="Free-text purchase request in natural language")
    urgency: Optional[str] = "NORMAL"  # NORMAL | URGENT | CRITICAL
    budget_code: Optional[str] = None
    preferred_vendor: Optional[str] = None


class RequisitionResult(BaseModel):
    requisition_id: str
    extracted_items: list[dict]
    total_estimated_cost: float
    budget_validation: dict
    vendor_recommendations: list[dict]
    policy_violations: list[str]
    approval_tier: str  # AUTO | MANAGER | VP | EXEC
    approval_required_by: Optional[str]
    recommended_action: str
    confidence: float
    processing_timestamp: str


class VendorSelectionRequest(BaseModel):
    item_description: str
    category: str
    estimated_quantity: int
    budget_limit: float
    delivery_timeline_days: int
    quality_requirements: Optional[str] = None


# ─────────────────────────────────────────────
# Vendor Knowledge Base (Vector DB)
# ─────────────────────────────────────────────

# Approved vendor catalog (in production: loaded from ERP/procurement system)
VENDOR_CATALOG = [
    {
        "vendor_id": "V001", "name": "TechSupply Corp", "category": "IT Hardware",
        "performance_score": 92, "price_tier": "STANDARD", "lead_time_days": 5,
        "approved": True, "contract_end": "2026-12-31",
        "description": "Laptops, desktops, monitors, peripherals, servers, networking equipment"
    },
    {
        "vendor_id": "V002", "name": "OfficeMax Pro", "category": "Office Supplies",
        "performance_score": 88, "price_tier": "BUDGET", "lead_time_days": 2,
        "approved": True, "contract_end": "2026-09-30",
        "description": "Paper, pens, folders, staplers, desk supplies, printing supplies"
    },
    {
        "vendor_id": "V003", "name": "CloudSoft Solutions", "category": "Software Licenses",
        "performance_score": 95, "price_tier": "PREMIUM", "lead_time_days": 1,
        "approved": True, "contract_end": "2027-03-31",
        "description": "Enterprise software, SaaS subscriptions, cloud services, licenses"
    },
    {
        "vendor_id": "V004", "name": "Industrial Direct", "category": "Manufacturing",
        "performance_score": 87, "price_tier": "STANDARD", "lead_time_days": 10,
        "approved": True, "contract_end": "2026-12-31",
        "description": "Industrial equipment, machinery parts, manufacturing supplies, tools"
    },
    {
        "vendor_id": "V005", "name": "GlobalTravel Corp", "category": "Travel",
        "performance_score": 91, "price_tier": "STANDARD", "lead_time_days": 1,
        "approved": True, "contract_end": "2027-06-30",
        "description": "Flights, hotels, car rentals, travel management, corporate travel"
    },
]

# Budget thresholds by approval tier
APPROVAL_THRESHOLDS = {
    "AUTO": 1000,        # Under $1K — auto-approve
    "MANAGER": 10000,    # $1K-$10K — manager approval
    "VP": 50000,         # $10K-$50K — VP approval
    "EXEC": 100000,      # $50K-$100K — exec approval
    "BOARD": float("inf")  # Over $100K — board approval
}

# Policy rules
RESTRICTED_CATEGORIES = ["Alcohol", "Personal Items", "Political Donations", "Entertainment (>$500/person)"]
PREFERRED_VENDOR_MANDATE_CATEGORIES = ["IT Hardware", "Software Licenses", "Travel"]


# ─────────────────────────────────────────────
# Procurement Tools
# ─────────────────────────────────────────────

@tool
def extract_purchase_intent(request_text: str) -> str:
    """
    Extract structured purchase information from a free-text purchase request.
    Identifies items, quantities, specifications, urgency, and business justification.
    Args:
        request_text: The natural language purchase request
    Returns:
        JSON with extracted items and purchase details
    """
    # This is a pass-through — the LLM handles extraction directly
    return f"Analyzing request: {request_text[:200]}..."


@tool
def find_approved_vendors(category: str, budget: float = 0) -> str:
    """
    Search the approved vendor catalog for vendors matching the purchase category.
    Args:
        category: Product/service category (e.g., 'IT Hardware', 'Office Supplies')
        budget: Budget limit for the purchase
    Returns:
        JSON list of approved vendors with performance scores and pricing
    """
    matching = [
        v for v in VENDOR_CATALOG
        if (category.lower() in v["category"].lower() or
            category.lower() in v["description"].lower())
        and v["approved"]
    ]

    if not matching:
        # Try broader category match
        category_words = category.lower().split()
        matching = [
            v for v in VENDOR_CATALOG
            if any(word in v["description"].lower() for word in category_words)
            and v["approved"]
        ]

    # Sort by performance score
    matching.sort(key=lambda x: x["performance_score"], reverse=True)

    if not matching:
        return json.dumps({
            "found": False,
            "vendors": [],
            "message": f"No approved vendors found for category '{category}'. New vendor approval required."
        })

    return json.dumps({
        "found": True,
        "vendors": matching[:3],  # Top 3 vendors
        "message": f"Found {len(matching)} approved vendors for '{category}'"
    })


@tool
def validate_budget(cost_center: str, estimated_total: float, category: str) -> str:
    """
    Validate that the estimated purchase amount is within budget for the cost center.
    Args:
        cost_center: The cost center code for budget allocation
        estimated_total: Total estimated cost of the purchase
        category: Purchase category
    Returns:
        Budget validation result with available budget and approval requirements
    """
    # Simulated budget data (in production: query ERP/financial system)
    budget_data = {
        "IT-001": {"annual_budget": 500000, "spent": 320000, "committed": 50000},
        "HR-001": {"annual_budget": 150000, "spent": 80000, "committed": 10000},
        "OPS-001": {"annual_budget": 200000, "spent": 120000, "committed": 30000},
        "SALES-001": {"annual_budget": 300000, "spent": 180000, "committed": 20000},
    }

    budget = budget_data.get(cost_center, {"annual_budget": 100000, "spent": 50000, "committed": 10000})
    available = budget["annual_budget"] - budget["spent"] - budget["committed"]
    within_budget = estimated_total <= available

    # Determine approval tier
    approval_tier = "AUTO"
    for tier, threshold in APPROVAL_THRESHOLDS.items():
        if estimated_total <= threshold:
            approval_tier = tier
            break

    return json.dumps({
        "cost_center": cost_center,
        "requested_amount": estimated_total,
        "available_budget": available,
        "within_budget": within_budget,
        "approval_tier": approval_tier,
        "budget_utilization_pct": round((budget["spent"] + estimated_total) / budget["annual_budget"] * 100, 1),
        "warning": "Budget utilization will exceed 90%" if (budget["spent"] + estimated_total) / budget["annual_budget"] > 0.9 else None
    })


@tool
def check_policy_compliance(category: str, items: str, requester_department: str) -> str:
    """
    Check whether the purchase request complies with procurement policies.
    Args:
        category: Purchase category
        items: Description of items to be purchased
        requester_department: The department making the request
    Returns:
        Policy compliance check result with any violations
    """
    violations = []
    warnings = []

    # Check restricted categories
    for restricted in RESTRICTED_CATEGORIES:
        if restricted.lower().split(" (")[0] in items.lower() or restricted.lower().split(" (")[0] in category.lower():
            violations.append(f"POLICY VIOLATION: '{restricted}' is on the restricted purchase list")

    # Check preferred vendor mandate
    if category in PREFERRED_VENDOR_MANDATE_CATEGORIES:
        warnings.append(f"NOTE: '{category}' requires use of pre-approved preferred vendors. Verify vendor is on approved list.")

    # Check single-source justification
    if "sole source" in items.lower() or "only vendor" in items.lower():
        warnings.append("NOTE: Single-source justification required. Documentation must be attached.")

    return json.dumps({
        "compliant": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "policy_reference": "Procurement Policy v3.2 — Section 4.1 Approved Categories",
        "compliance_score": 100 if len(violations) == 0 else max(0, 100 - (len(violations) * 30))
    })


@tool
def estimate_cost(items_description: str, quantity: int, category: str) -> str:
    """
    Estimate the cost of a purchase based on item description, quantity, and category.
    Args:
        items_description: Description of the items
        quantity: Number of units
        category: Purchase category
    Returns:
        Cost estimate with confidence range
    """
    # Simplified cost estimation (in production: query pricing database or APIs)
    cost_benchmarks = {
        "laptop": (800, 2500), "desktop": (600, 2000), "monitor": (200, 800),
        "software license": (50, 500), "office chair": (150, 600), "desk": (200, 800),
        "server": (3000, 15000), "printer": (200, 2000), "phone": (200, 1000),
        "subscription": (20, 200),  # per month
    }

    items_lower = items_description.lower()
    matched_cost = None

    for item, (low, high) in cost_benchmarks.items():
        if item in items_lower:
            matched_cost = (low * quantity, high * quantity)
            break

    if matched_cost is None:
        # Default estimate
        matched_cost = (100 * quantity, 500 * quantity)

    return json.dumps({
        "items": items_description,
        "quantity": quantity,
        "estimated_cost_low": matched_cost[0],
        "estimated_cost_high": matched_cost[1],
        "estimated_cost_mid": (matched_cost[0] + matched_cost[1]) / 2,
        "confidence": "MEDIUM",
        "note": "Estimate based on market benchmarks. Final pricing confirmed by vendor RFQ."
    })


# ─────────────────────────────────────────────
# LangChain Requisition Agent
# ─────────────────────────────────────────────

def create_requisition_agent():
    """Create the LangChain requisition intelligence agent."""
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
    )

    tools = [
        extract_purchase_intent,
        find_approved_vendors,
        validate_budget,
        check_policy_compliance,
        estimate_cost,
    ]

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are ProcureFlow AI's Requisition Intelligence Agent — an expert procurement analyst.

        Your role is to:
        1. Parse free-text purchase requests and extract structured information
        2. Identify purchase categories, items, quantities, and specifications
        3. Find appropriate approved vendors for each item category
        4. Validate budget availability and compliance
        5. Determine the correct approval tier based on total cost
        6. Flag any policy violations or procurement risks

        Always be thorough and systematic. Use your tools in sequence:
        1. First estimate costs for the items
        2. Find approved vendors for each category
        3. Validate budget against the cost center
        4. Check policy compliance
        5. Summarize with recommendations

        Return a structured JSON response with all findings.
        """),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=15)


_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = create_requisition_agent()
    return _agent


# ─────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────

@app.post("/process-requisition", response_model=RequisitionResult)
async def process_requisition(request: RequisitionRequest):
    """
    Process a purchase requisition through the AI agent.
    Called by UiPath Maestro BPMN at the Requisition Processing task.
    """
    logger.info(f"Processing requisition from {request.requester_id}: {request.request_text[:100]}")

    try:
        agent = get_agent()

        prompt = f"""
        Process this purchase requisition:

        Requester: {request.requester_id}
        Department: {request.department}
        Cost Center: {request.cost_center}
        Urgency: {request.urgency}
        Preferred Vendor: {request.preferred_vendor or 'None specified'}

        Purchase Request:
        "{request.request_text}"

        Please:
        1. Extract all items, quantities, and specifications from the request
        2. Estimate costs for each item
        3. Find approved vendors for each item category
        4. Validate the total against the {request.cost_center} budget
        5. Check policy compliance
        6. Determine required approval tier
        7. Provide a recommendation

        Return JSON with: extracted_items, total_estimated_cost, budget_validation,
        vendor_recommendations, policy_violations, approval_tier, recommended_action, confidence
        """

        result = agent.invoke({"input": prompt})
        output = result["output"]

        # Parse agent output
        try:
            if "```json" in output:
                json_str = output.split("```json")[1].split("```")[0].strip()
            elif "```" in output:
                json_str = output.split("```")[1].split("```")[0].strip()
            else:
                json_str = output.strip()

            parsed = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Could not parse JSON output, using structured fallback")
            parsed = {
                "extracted_items": [{"description": request.request_text, "quantity": 1, "estimated_cost": 0}],
                "total_estimated_cost": 0,
                "budget_validation": {"within_budget": True, "approval_tier": "MANAGER"},
                "vendor_recommendations": [],
                "policy_violations": [],
                "approval_tier": "MANAGER",
                "recommended_action": "PROCEED_WITH_STANDARD_APPROVAL",
                "confidence": 0.5
            }

        # Determine approval required by (SLA)
        urgency_sla = {
            "CRITICAL": "2 hours",
            "URGENT": "4 hours",
            "NORMAL": "48 hours"
        }

        return RequisitionResult(
            requisition_id=f"REQ-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            extracted_items=parsed.get("extracted_items", []),
            total_estimated_cost=parsed.get("total_estimated_cost", 0),
            budget_validation=parsed.get("budget_validation", {}),
            vendor_recommendations=parsed.get("vendor_recommendations", []),
            policy_violations=parsed.get("policy_violations", []),
            approval_tier=parsed.get("approval_tier", "MANAGER"),
            approval_required_by=urgency_sla.get(request.urgency, "48 hours"),
            recommended_action=parsed.get("recommended_action", "PROCEED_WITH_STANDARD_APPROVAL"),
            confidence=parsed.get("confidence", 0.8),
            processing_timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Requisition processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Requisition processing failed: {str(e)}")


@app.post("/recommend-vendor")
async def recommend_vendor(request: VendorSelectionRequest):
    """Recommend the best vendor for a specific purchase."""
    vendors_json = find_approved_vendors.invoke({
        "category": request.category,
        "budget": request.budget_limit
    })
    vendors = json.loads(vendors_json)

    return {
        "item": request.item_description,
        "category": request.category,
        "budget_limit": request.budget_limit,
        "recommendations": vendors.get("vendors", []),
        "recommendation": vendors.get("vendors", [{}])[0] if vendors.get("vendors") else None
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "agent": "requisition_intelligence", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
