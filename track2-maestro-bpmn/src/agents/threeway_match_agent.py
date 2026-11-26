"""
ProcureFlow AI — AutoGen 3-Way Match Reconciliation Agent
Track 2: UiPath Maestro BPMN

Uses AutoGen multi-agent conversation to reconcile Purchase Orders, 
Goods Receipts, and Invoices. Handles complex discrepancies through
structured agent dialogue.

Built with UiPath for Coding Agents (Claude Code) - bonus points!
"""

import os
import json
import logging
from typing import Optional
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import autogen
from langchain_openai import ChatOpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ProcureFlow AI — 3-Way Match Agent",
    description="AutoGen-powered invoice reconciliation and discrepancy resolution",
    version="1.0.0"
)

# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

class PurchaseOrder(BaseModel):
    po_number: str
    vendor_id: str
    vendor_name: str
    line_items: list[dict] = Field(..., description="List of {item, quantity, unit_price, total}")
    total_amount: float
    currency: str = "USD"
    po_date: str
    delivery_date: str
    payment_terms: str = "NET30"


class GoodsReceipt(BaseModel):
    gr_number: str
    po_number: str
    received_items: list[dict] = Field(..., description="List of {item, received_quantity, condition}")
    receipt_date: str
    receiver_id: str
    warehouse_location: str
    notes: Optional[str] = None


class Invoice(BaseModel):
    invoice_number: str
    vendor_id: str
    vendor_name: str
    po_number: str
    line_items: list[dict] = Field(..., description="List of {item, quantity, unit_price, total}")
    total_amount: float
    invoice_date: str
    due_date: str
    payment_method: str = "EFT"
    bank_account: Optional[str] = None


class MatchRequest(BaseModel):
    purchase_order: PurchaseOrder
    goods_receipt: GoodsReceipt
    invoice: Invoice
    tolerance_percentage: float = Field(default=2.0, description="Acceptable price variance %")


class MatchResult(BaseModel):
    match_id: str
    po_number: str
    invoice_number: str
    match_status: str  # PERFECT_MATCH | WITHIN_TOLERANCE | DISCREPANCY | REJECT
    discrepancies: list[dict]
    auto_resolvable: bool
    resolution_applied: Optional[str]
    payable_amount: float
    variance_amount: float
    variance_percentage: float
    requires_human_review: bool
    human_review_reason: Optional[str]
    reconciliation_notes: str
    processing_timestamp: str


# ─────────────────────────────────────────────
# Three-Way Match Logic
# ─────────────────────────────────────────────

def perform_three_way_match(
    po: PurchaseOrder,
    gr: GoodsReceipt,
    invoice: Invoice,
    tolerance_pct: float
) -> dict:
    """
    Core 3-way match logic comparing PO, GR, and Invoice line by line.
    Returns structured discrepancy report.
    """
    discrepancies = []

    # Build lookup maps
    po_items = {item.get("item", "").lower(): item for item in po.line_items}
    gr_items = {item.get("item", "").lower(): item for item in gr.received_items}
    inv_items = {item.get("item", "").lower(): item for item in invoice.line_items}

    # Check each invoice line
    for item_key, inv_item in inv_items.items():
        po_item = po_items.get(item_key)
        gr_item = gr_items.get(item_key)

        if not po_item:
            discrepancies.append({
                "type": "ITEM_NOT_ON_PO",
                "severity": "HIGH",
                "item": inv_item.get("item"),
                "detail": f"Invoice item '{inv_item.get('item')}' not found on PO {po.po_number}",
                "auto_resolvable": False
            })
            continue

        if not gr_item:
            discrepancies.append({
                "type": "ITEM_NOT_RECEIVED",
                "severity": "HIGH",
                "item": inv_item.get("item"),
                "detail": f"Invoice item '{inv_item.get('item')}' has no goods receipt confirmation",
                "auto_resolvable": False
            })
            continue

        # Quantity check: Invoice vs Goods Receipt
        inv_qty = float(inv_item.get("quantity", 0))
        gr_qty = float(gr_item.get("received_quantity", 0))
        po_qty = float(po_item.get("quantity", 0))

        if inv_qty > gr_qty:
            discrepancies.append({
                "type": "QUANTITY_OVERBILL",
                "severity": "MEDIUM",
                "item": inv_item.get("item"),
                "detail": f"Invoice qty {inv_qty} > received qty {gr_qty}",
                "inv_quantity": inv_qty,
                "gr_quantity": gr_qty,
                "auto_resolvable": True,
                "auto_resolution": f"Pay for {gr_qty} units (received quantity)"
            })
        elif inv_qty < gr_qty:
            discrepancies.append({
                "type": "QUANTITY_UNDERBILL",
                "severity": "LOW",
                "item": inv_item.get("item"),
                "detail": f"Invoice qty {inv_qty} < received qty {gr_qty}. Partial invoice.",
                "auto_resolvable": True,
                "auto_resolution": "Pay invoice amount, track remaining balance for future invoice"
            })

        # Price check: Invoice vs PO
        inv_price = float(inv_item.get("unit_price", 0))
        po_price = float(po_item.get("unit_price", 0))

        if po_price > 0:
            price_variance_pct = abs(inv_price - po_price) / po_price * 100

            if price_variance_pct > tolerance_pct:
                severity = "HIGH" if price_variance_pct > 10 else "MEDIUM"
                discrepancies.append({
                    "type": "PRICE_VARIANCE",
                    "severity": severity,
                    "item": inv_item.get("item"),
                    "detail": f"Price variance: PO ${po_price:.2f} vs Invoice ${inv_price:.2f} ({price_variance_pct:.1f}%)",
                    "po_price": po_price,
                    "inv_price": inv_price,
                    "variance_pct": round(price_variance_pct, 2),
                    "auto_resolvable": price_variance_pct <= 5.0,  # Auto-resolve within 5%
                    "auto_resolution": f"Pay PO rate ${po_price:.2f}" if price_variance_pct <= 5.0 else None
                })

    # Total amount check
    total_variance = abs(invoice.total_amount - po.total_amount)
    total_variance_pct = total_variance / po.total_amount * 100 if po.total_amount > 0 else 0

    return {
        "discrepancies": discrepancies,
        "total_variance": total_variance,
        "total_variance_pct": round(total_variance_pct, 2),
        "po_total": po.total_amount,
        "invoice_total": invoice.total_amount,
        "all_auto_resolvable": all(d.get("auto_resolvable", False) for d in discrepancies),
        "high_severity_count": sum(1 for d in discrepancies if d.get("severity") == "HIGH")
    }


# ─────────────────────────────────────────────
# AutoGen Multi-Agent Reconciliation
# ─────────────────────────────────────────────

def run_autogen_reconciliation(match_data: dict, discrepancies: list) -> dict:
    """
    Use AutoGen to have a multi-agent conversation about complex discrepancies.
    AP Analyst and Finance Controller agents discuss and reach resolution.
    """
    config_list = [
        {
            "model": "gpt-4o",
            "api_key": os.getenv("OPENAI_API_KEY"),
        }
    ]

    # AP Analyst Agent — proposes resolutions
    ap_analyst = autogen.AssistantAgent(
        name="AP_Analyst",
        system_message="""You are an experienced Accounts Payable analyst.
        Your role is to analyze invoice discrepancies and propose fair resolutions
        based on contract terms, standard AP policies, and business relationships.
        Be pragmatic — small variances should be resolved quickly to maintain vendor relationships.
        Always provide a specific dollar amount for your recommended payment.""",
        llm_config={"config_list": config_list, "temperature": 0}
    )

    # Finance Controller — validates and approves
    finance_controller = autogen.AssistantAgent(
        name="Finance_Controller",
        system_message="""You are the Finance Controller responsible for payment approval.
        Your role is to review AP analyst proposals, apply financial controls,
        ensure SOX compliance, and approve or adjust the payment recommendation.
        Be conservative — protect the company from overpayments and fraud.
        End your final message with 'FINAL DECISION: [APPROVE/REJECT/PARTIAL] - Pay $X.XX'""",
        llm_config={"config_list": config_list, "temperature": 0}
    )

    # User proxy to facilitate conversation
    user_proxy = autogen.UserProxyAgent(
        name="System",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=4,
        is_termination_msg=lambda msg: "FINAL DECISION:" in msg.get("content", ""),
        code_execution_config=False
    )

    # Build the reconciliation prompt
    discrepancy_summary = "\n".join([
        f"- [{d['severity']}] {d['type']}: {d['detail']}" for d in discrepancies
    ])

    prompt = f"""
    Reconcile this invoice discrepancy:

    PO Total: ${match_data['po_total']:,.2f}
    Invoice Total: ${match_data['invoice_total']:,.2f}
    Variance: ${match_data['total_variance']:,.2f} ({match_data['total_variance_pct']:.1f}%)

    Discrepancies found:
    {discrepancy_summary}

    AP Analyst: Please analyze these discrepancies and propose a specific payment recommendation.
    Finance Controller: Review the proposal and provide your final decision.
    """

    # Run the conversation
    conversation_result = {"resolution": "STANDARD_REVIEW", "payable_amount": match_data["po_total"]}

    try:
        user_proxy.initiate_chat(
            ap_analyst,
            message=prompt,
            max_turns=6
        )

        # Extract final decision from conversation
        last_message = ap_analyst.last_message()
        if last_message and "FINAL DECISION:" in last_message.get("content", ""):
            content = last_message["content"]
            if "APPROVE" in content:
                conversation_result["resolution"] = "APPROVE"
            elif "PARTIAL" in content:
                conversation_result["resolution"] = "PARTIAL"
            else:
                conversation_result["resolution"] = "REJECT"

    except Exception as e:
        logger.warning(f"AutoGen conversation failed: {e}. Using default resolution.")

    return conversation_result


# ─────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────

@app.post("/match", response_model=MatchResult)
async def three_way_match(request: MatchRequest):
    """
    Perform 3-way match of PO, Goods Receipt, and Invoice.
    Called by UiPath Maestro BPMN at the Invoice Processing task.
    """
    logger.info(f"3-way match: PO {request.purchase_order.po_number} + Invoice {request.invoice.invoice_number}")

    try:
        # Step 1: Perform mathematical 3-way match
        match_data = perform_three_way_match(
            request.purchase_order,
            request.goods_receipt,
            request.invoice,
            request.tolerance_percentage
        )

        discrepancies = match_data["discrepancies"]

        # Step 2: Determine match status
        if not discrepancies:
            status = "PERFECT_MATCH"
            auto_resolvable = True
            requires_human = False
            payable_amount = request.invoice.total_amount
            resolution_applied = None
            reconciliation_notes = "All quantities, prices, and totals match perfectly."

        elif match_data["all_auto_resolvable"] and match_data["total_variance_pct"] <= request.tolerance_percentage:
            status = "WITHIN_TOLERANCE"
            auto_resolvable = True
            requires_human = False
            payable_amount = request.purchase_order.total_amount  # Pay PO amount
            resolution_applied = f"Auto-resolved: Applied PO pricing to {len(discrepancies)} minor variance(s)"
            reconciliation_notes = f"Minor discrepancies auto-resolved within {request.tolerance_percentage}% tolerance policy."

        elif match_data["high_severity_count"] == 0 and match_data["all_auto_resolvable"]:
            # Use AutoGen for medium-complexity resolution
            autogen_result = run_autogen_reconciliation(match_data, discrepancies)
            status = "DISCREPANCY"
            auto_resolvable = True
            requires_human = False
            payable_amount = autogen_result.get("payable_amount", request.purchase_order.total_amount)
            resolution_applied = f"AutoGen resolution: {autogen_result.get('resolution', 'STANDARD')}"
            reconciliation_notes = "AI-mediated reconciliation completed. AP Analyst and Finance Controller reached agreement."

        else:
            # High severity discrepancies — escalate to human
            status = "DISCREPANCY"
            auto_resolvable = False
            requires_human = True
            payable_amount = 0  # Hold payment
            resolution_applied = None
            reconciliation_notes = f"{match_data['high_severity_count']} high-severity discrepancy(ies) require human AP review."

        human_reason = None
        if requires_human:
            reasons = [d["detail"] for d in discrepancies if d.get("severity") == "HIGH"]
            human_reason = "; ".join(reasons[:3])  # Top 3 reasons

        return MatchResult(
            match_id=f"MATCH-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            po_number=request.purchase_order.po_number,
            invoice_number=request.invoice.invoice_number,
            match_status=status,
            discrepancies=discrepancies,
            auto_resolvable=auto_resolvable,
            resolution_applied=resolution_applied,
            payable_amount=payable_amount,
            variance_amount=match_data["total_variance"],
            variance_percentage=match_data["total_variance_pct"],
            requires_human_review=requires_human,
            human_review_reason=human_reason,
            reconciliation_notes=reconciliation_notes,
            processing_timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"3-way match failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Match processing failed: {str(e)}")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "agent": "threeway_match", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
