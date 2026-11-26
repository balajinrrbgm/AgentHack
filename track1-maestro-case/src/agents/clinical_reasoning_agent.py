"""
MediClaim Guardian — Clinical Reasoning Agent
Track 1: UiPath Maestro Case

This coded agent provides clinical necessity validation and complexity scoring
for healthcare insurance claims using LangChain + GPT-4o.

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
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MediClaim Guardian — Clinical Reasoning Agent",
    description="AI-powered clinical necessity validation for healthcare claims",
    version="1.0.0"
)

# ─────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────

class ClaimData(BaseModel):
    claim_id: str
    patient_id: str
    procedure_codes: list[str] = Field(..., description="CPT procedure codes")
    diagnosis_codes: list[str] = Field(..., description="ICD-10 diagnosis codes")
    provider_npi: str
    service_date: str
    place_of_service: str
    units: int = 1
    billed_amount: float
    clinical_notes: Optional[str] = None
    prior_auth_number: Optional[str] = None


class TriageResult(BaseModel):
    claim_id: str
    complexity_score: int = Field(..., ge=0, le=100)
    risk_tier: str  # LOW, MEDIUM, HIGH
    fraud_flags: list[str]
    clinical_concerns: list[str]
    recommended_path: str
    confidence: float
    reasoning_summary: str
    processing_timestamp: str


# ─────────────────────────────────────────────
# Clinical Reasoning Tools
# ─────────────────────────────────────────────

@tool
def lookup_icd10_code(code: str) -> dict:
    """
    Look up ICD-10 diagnosis code to validate it exists and get description.
    Returns code details including validity, description, and category.
    """
    # In production: query clinical database or API
    # Simulated response for demo
    icd10_database = {
        "J18.9": {"description": "Pneumonia, unspecified organism", "category": "Respiratory", "valid": True},
        "I25.10": {"description": "Atherosclerotic heart disease of native coronary artery", "category": "Cardiac", "valid": True},
        "M54.5": {"description": "Low back pain", "category": "Musculoskeletal", "valid": True},
        "Z23": {"description": "Encounter for immunization", "category": "Preventive", "valid": True},
        "F32.1": {"description": "Major depressive disorder, single episode, moderate", "category": "Mental Health", "valid": True},
    }
    return icd10_database.get(code, {"description": "Unknown code", "valid": False, "code": code})


@tool
def lookup_cpt_code(code: str) -> dict:
    """
    Look up CPT procedure code to validate it and check coverage policies.
    Returns procedure details, typical cost range, and coverage notes.
    """
    cpt_database = {
        "99213": {"description": "Office visit, established patient, low complexity", "typical_cost_low": 80, "typical_cost_high": 150, "requires_auth": False},
        "99214": {"description": "Office visit, established patient, moderate complexity", "typical_cost_low": 120, "typical_cost_high": 220, "requires_auth": False},
        "27447": {"description": "Total knee arthroplasty", "typical_cost_low": 15000, "typical_cost_high": 35000, "requires_auth": True},
        "90834": {"description": "Psychotherapy, 45 minutes", "typical_cost_low": 100, "typical_cost_high": 200, "requires_auth": False},
        "93000": {"description": "Electrocardiogram, routine", "typical_cost_low": 50, "typical_cost_high": 120, "requires_auth": False},
        "99285": {"description": "Emergency department visit, high complexity", "typical_cost_low": 800, "typical_cost_high": 2500, "requires_auth": False},
    }
    return cpt_database.get(code, {"description": "Unrecognized CPT code", "requires_auth": True, "typical_cost_low": 0, "typical_cost_high": 0})


@tool
def check_procedure_diagnosis_alignment(procedure_code: str, diagnosis_code: str) -> dict:
    """
    Verify that the procedure code is clinically appropriate for the given diagnosis.
    Returns alignment score and any misalignment concerns.
    """
    # Medical appropriateness rules (simplified for demo)
    appropriate_pairs = {
        ("27447", "M17.11"): {"aligned": True, "note": "Knee replacement appropriate for severe osteoarthritis"},
        ("99213", "J18.9"): {"aligned": True, "note": "Office visit appropriate for pneumonia follow-up"},
        ("93000", "I25.10"): {"aligned": True, "note": "ECG appropriate for coronary artery disease monitoring"},
        ("90834", "F32.1"): {"aligned": True, "note": "Psychotherapy appropriate for major depressive disorder"},
        ("27447", "M54.5"): {"aligned": False, "note": "ALERT: Knee replacement is not indicated for low back pain — possible upcoding"},
        ("99285", "Z23"): {"aligned": False, "note": "ALERT: Emergency visit is not appropriate for routine immunization — review required"},
    }

    key = (procedure_code, diagnosis_code)
    result = appropriate_pairs.get(key, {
        "aligned": True,
        "note": "No specific misalignment rule found — standard review",
        "requires_clinical_review": False
    })
    return {"procedure": procedure_code, "diagnosis": diagnosis_code, **result}


@tool
def check_billing_patterns(provider_npi: str, procedure_code: str) -> dict:
    """
    Analyze provider billing patterns for this procedure code.
    Flags statistical anomalies that may indicate fraud or abuse.
    """
    # In production: query billing analytics database
    # Simulated for demo
    import random
    random.seed(hash(provider_npi + procedure_code) % 1000)

    avg_frequency = random.randint(5, 50)
    provider_frequency = random.randint(1, 100)
    percentile = min(99, int((provider_frequency / 100) * 100))

    flags = []
    if percentile > 95:
        flags.append(f"Provider billing rate at {percentile}th percentile — significantly above average")
    if provider_frequency > avg_frequency * 3:
        flags.append("Provider billing 3x above peer average — statistical outlier")

    return {
        "provider_npi": provider_npi,
        "procedure_code": procedure_code,
        "provider_frequency_per_month": provider_frequency,
        "peer_average_per_month": avg_frequency,
        "percentile": percentile,
        "fraud_flags": flags,
        "risk_level": "HIGH" if len(flags) > 0 else "LOW"
    }


@tool
def calculate_claim_cost_reasonableness(
    procedure_code: str,
    billed_amount: float,
    place_of_service: str
) -> dict:
    """
    Assess whether the billed amount is reasonable for the procedure and service location.
    Returns reasonableness score and any overcharge indicators.
    """
    cpt_info = lookup_cpt_code.invoke(procedure_code)

    if not isinstance(cpt_info, dict):
        return {"reasonable": True, "score": 75, "note": "Unable to determine reasonableness"}

    low = cpt_info.get("typical_cost_low", 0)
    high = cpt_info.get("typical_cost_high", float("inf"))

    # Apply location multiplier (ER is higher, office is standard)
    multiplier = 1.5 if place_of_service == "23" else 1.0  # 23 = Emergency Room

    adjusted_high = high * multiplier

    if billed_amount <= adjusted_high:
        return {"reasonable": True, "score": 90, "billed": billed_amount, "expected_max": adjusted_high}
    elif billed_amount <= adjusted_high * 2:
        return {"reasonable": False, "score": 50, "billed": billed_amount, "expected_max": adjusted_high,
                "note": f"Billed amount ${billed_amount:.2f} exceeds typical maximum of ${adjusted_high:.2f}"}
    else:
        return {"reasonable": False, "score": 10, "billed": billed_amount, "expected_max": adjusted_high,
                "note": f"ALERT: Billed amount ${billed_amount:.2f} is {billed_amount/adjusted_high:.1f}x the expected maximum — significant overcharge flag"}


# ─────────────────────────────────────────────
# LangChain Agent Setup
# ─────────────────────────────────────────────

def create_clinical_agent():
    """Create the LangChain clinical reasoning agent with all tools."""
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
    )

    tools = [
        lookup_icd10_code,
        lookup_cpt_code,
        check_procedure_diagnosis_alignment,
        check_billing_patterns,
        calculate_claim_cost_reasonableness,
    ]

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are MediClaim Guardian's Clinical Reasoning Agent — a senior medical claims analyst with expertise in:
        - Clinical necessity validation (MCG and InterQual guidelines)
        - ICD-10 and CPT code analysis and appropriateness
        - Healthcare fraud detection and abuse patterns
        - Insurance coverage policies and authorization requirements

        Your job is to analyze healthcare insurance claims and provide:
        1. A complexity score (0-100) where 0=routine, 100=extremely complex/suspicious
        2. Identified fraud flags and clinical concerns
        3. A recommended processing path: AUTO_APPROVE, AUTO_DENY, STANDARD_REVIEW, EXPERT_REVIEW, FRAUD_INVESTIGATION
        4. A clear, actionable reasoning summary for case managers

        ALWAYS use your tools to validate codes and check billing patterns before scoring.
        Be thorough but efficient. Flag genuine concerns — don't over-investigate routine claims.
        """),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=10)


# Initialize agent (lazy load in production)
_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = create_clinical_agent()
    return _agent


# ─────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────

@app.post("/triage", response_model=TriageResult)
async def triage_claim(claim: ClaimData):
    """
    Triage a healthcare claim for complexity, fraud risk, and processing path.
    Called by UiPath Maestro Case after document extraction.
    """
    logger.info(f"Triaging claim: {claim.claim_id}")

    try:
        agent = get_agent()

        # Build the analysis prompt
        claim_summary = f"""
        Analyze this healthcare insurance claim:

        Claim ID: {claim.claim_id}
        Patient ID: {claim.patient_id}
        Service Date: {claim.service_date}
        Place of Service: {claim.place_of_service}
        Provider NPI: {claim.provider_npi}
        Billed Amount: ${claim.billed_amount:,.2f}
        Units: {claim.units}
        Prior Auth Number: {claim.prior_auth_number or 'None provided'}

        Procedure Codes (CPT): {', '.join(claim.procedure_codes)}
        Diagnosis Codes (ICD-10): {', '.join(claim.diagnosis_codes)}

        Clinical Notes: {claim.clinical_notes or 'None provided'}

        Please:
        1. Validate each procedure and diagnosis code
        2. Check procedure-diagnosis alignment for each pair
        3. Analyze billing patterns for this provider and procedure combination
        4. Assess cost reasonableness
        5. Provide a final complexity score (0-100), list all fraud flags and clinical concerns,
           and recommend a processing path (AUTO_APPROVE, AUTO_DENY, STANDARD_REVIEW, EXPERT_REVIEW, or FRAUD_INVESTIGATION)

        Return a structured JSON response with: complexity_score, risk_tier, fraud_flags (list),
        clinical_concerns (list), recommended_path, confidence (0.0-1.0), reasoning_summary
        """

        result = agent.invoke({"input": claim_summary})
        output = result["output"]

        # Parse JSON from agent output
        try:
            # Extract JSON if embedded in markdown code block
            if "```json" in output:
                json_str = output.split("```json")[1].split("```")[0].strip()
            elif "```" in output:
                json_str = output.split("```")[1].split("```")[0].strip()
            else:
                json_str = output.strip()

            parsed = json.loads(json_str)
        except json.JSONDecodeError:
            # Fallback: extract key fields from text response
            logger.warning(f"Could not parse JSON from agent output, using defaults for claim {claim.claim_id}")
            parsed = {
                "complexity_score": 50,
                "risk_tier": "MEDIUM",
                "fraud_flags": [],
                "clinical_concerns": ["Agent output parsing failed — manual review recommended"],
                "recommended_path": "STANDARD_REVIEW",
                "confidence": 0.5,
                "reasoning_summary": output[:500]
            }

        return TriageResult(
            claim_id=claim.claim_id,
            complexity_score=parsed.get("complexity_score", 50),
            risk_tier=parsed.get("risk_tier", "MEDIUM"),
            fraud_flags=parsed.get("fraud_flags", []),
            clinical_concerns=parsed.get("clinical_concerns", []),
            recommended_path=parsed.get("recommended_path", "STANDARD_REVIEW"),
            confidence=parsed.get("confidence", 0.7),
            reasoning_summary=parsed.get("reasoning_summary", "See detailed analysis"),
            processing_timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Triage failed for claim {claim.claim_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Clinical analysis failed: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint for UiPath connectivity monitoring."""
    return {
        "status": "healthy",
        "agent": "clinical_reasoning",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/batch-triage")
async def batch_triage(claims: list[ClaimData]):
    """Batch triage multiple claims (used for queue processing)."""
    if len(claims) > 50:
        raise HTTPException(status_code=400, detail="Batch size limited to 50 claims")

    results = []
    for claim in claims:
        try:
            result = await triage_claim(claim)
            results.append(result)
        except Exception as e:
            results.append({
                "claim_id": claim.claim_id,
                "error": str(e),
                "recommended_path": "STANDARD_REVIEW"
            })

    return {"batch_id": datetime.utcnow().isoformat(), "results": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
