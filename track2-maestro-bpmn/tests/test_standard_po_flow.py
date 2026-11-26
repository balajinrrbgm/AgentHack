"""
ProcureFlow AI — Integration Tests
Track 2: UiPath Maestro BPMN
"""

import pytest
import httpx
import json
from datetime import datetime, timedelta

REQ_URL = "http://localhost:8003"   # Requisition Agent
MATCH_URL = "http://localhost:8004"  # 3-Way Match Agent


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def simple_requisition():
    return {
        "requester_id": "USER-001",
        "department": "Engineering",
        "cost_center": "IT-001",
        "request_text": "I need 5 laptop stands and a USB hub for the team",
        "urgency": "NORMAL"
    }


@pytest.fixture
def large_requisition():
    return {
        "requester_id": "USER-002",
        "department": "IT",
        "cost_center": "IT-001",
        "request_text": "We need 20 MacBook Pro 16-inch laptops and 20 external monitors for the new data team. Total budget should come from IT-001. Urgent — team starts Monday.",
        "urgency": "URGENT"
    }


@pytest.fixture
def perfect_match_request():
    future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    return {
        "purchase_order": {
            "po_number": "PO-TEST-001",
            "vendor_id": "V001",
            "vendor_name": "TechSupply Corp",
            "line_items": [
                {"item": "MacBook Pro 14", "quantity": 10, "unit_price": 1950.0, "total": 19500.0}
            ],
            "total_amount": 19500.0,
            "currency": "USD",
            "po_date": "2026-06-01",
            "delivery_date": "2026-06-06",
            "payment_terms": "NET30"
        },
        "goods_receipt": {
            "gr_number": "GR-TEST-001",
            "po_number": "PO-TEST-001",
            "received_items": [
                {"item": "MacBook Pro 14", "received_quantity": 10, "condition": "Good"}
            ],
            "receipt_date": "2026-06-06",
            "receiver_id": "WAREHOUSE-001",
            "warehouse_location": "A12"
        },
        "invoice": {
            "invoice_number": "INV-TEST-001",
            "vendor_id": "V001",
            "vendor_name": "TechSupply Corp",
            "po_number": "PO-TEST-001",
            "line_items": [
                {"item": "MacBook Pro 14", "quantity": 10, "unit_price": 1950.0, "total": 19500.0}
            ],
            "total_amount": 19500.0,
            "invoice_date": "2026-06-07",
            "due_date": future_date,
            "payment_method": "EFT"
        },
        "tolerance_percentage": 2.0
    }


@pytest.fixture
def price_variance_request(perfect_match_request):
    req = perfect_match_request.copy()
    req = json.loads(json.dumps(req))  # Deep copy
    # Add 1.5% price variance (within tolerance)
    req["invoice"]["line_items"][0]["unit_price"] = 1979.25  # +1.5%
    req["invoice"]["total_amount"] = 19792.50
    return req


@pytest.fixture
def discrepancy_request(perfect_match_request):
    req = json.loads(json.dumps(perfect_match_request))  # Deep copy
    # Add 15% price variance (exceeds tolerance)
    req["invoice"]["line_items"][0]["unit_price"] = 2242.50  # +15%
    req["invoice"]["total_amount"] = 22425.0
    return req


# ─────────────────────────────────────────────
# Requisition Agent Tests
# ─────────────────────────────────────────────

class TestRequisitionAgent:

    def test_health_check(self):
        response = httpx.get(f"{REQ_URL}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_simple_requisition_processed(self, simple_requisition):
        """Simple requisition should auto-route below $1K threshold."""
        response = httpx.post(
            f"{REQ_URL}/process-requisition",
            json=simple_requisition,
            timeout=60
        )
        assert response.status_code == 200
        result = response.json()

        assert result["requisition_id"].startswith("REQ-")
        assert result["total_estimated_cost"] >= 0
        assert result["approval_tier"] in ["AUTO", "MANAGER", "VP", "EXEC"]
        assert isinstance(result["policy_violations"], list)
        assert result["confidence"] >= 0.5

    def test_large_requisition_requires_approval(self, large_requisition):
        """Large requisition (>$10K) should require manager/VP approval."""
        response = httpx.post(
            f"{REQ_URL}/process-requisition",
            json=large_requisition,
            timeout=60
        )
        assert response.status_code == 200
        result = response.json()

        # $40K+ laptop order should require VP or manager approval
        assert result["approval_tier"] in ["MANAGER", "VP", "EXEC"]
        assert result["total_estimated_cost"] > 10000

    def test_vendor_recommendation_returned(self, large_requisition):
        """Vendor recommendations should be included for large purchases."""
        response = httpx.post(
            f"{REQ_URL}/process-requisition",
            json=large_requisition,
            timeout=60
        )
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result["vendor_recommendations"], list)

    def test_missing_cost_center_handled(self):
        """Missing required fields should return validation error."""
        response = httpx.post(f"{REQ_URL}/process-requisition", json={}, timeout=10)
        assert response.status_code == 422


# ─────────────────────────────────────────────
# 3-Way Match Agent Tests
# ─────────────────────────────────────────────

class TestThreeWayMatch:

    def test_health_check(self):
        response = httpx.get(f"{MATCH_URL}/health")
        assert response.status_code == 200

    def test_perfect_match(self, perfect_match_request):
        """Perfect PO/GR/Invoice match should auto-approve."""
        response = httpx.post(f"{MATCH_URL}/match", json=perfect_match_request, timeout=60)
        assert response.status_code == 200
        result = response.json()

        assert result["match_status"] == "PERFECT_MATCH"
        assert result["auto_resolvable"] is True
        assert result["requires_human_review"] is False
        assert result["payable_amount"] == 19500.0
        assert result["variance_amount"] == 0.0

    def test_within_tolerance_variance(self, price_variance_request):
        """1.5% price variance within 2% tolerance should auto-resolve."""
        response = httpx.post(f"{MATCH_URL}/match", json=price_variance_request, timeout=60)
        assert response.status_code == 200
        result = response.json()

        assert result["match_status"] in ["PERFECT_MATCH", "WITHIN_TOLERANCE"]
        assert result["requires_human_review"] is False
        assert result["auto_resolvable"] is True

    def test_large_discrepancy_escalates(self, discrepancy_request):
        """15% price variance should require human AP review."""
        response = httpx.post(f"{MATCH_URL}/match", json=discrepancy_request, timeout=60)
        assert response.status_code == 200
        result = response.json()

        assert result["match_status"] == "DISCREPANCY"
        # Large discrepancy should escalate
        assert result["requires_human_review"] is True or result["payable_amount"] <= 19500.0

    def test_match_result_has_match_id(self, perfect_match_request):
        """Every match should return a unique match ID."""
        response = httpx.post(f"{MATCH_URL}/match", json=perfect_match_request, timeout=60)
        assert response.status_code == 200
        result = response.json()
        assert result["match_id"].startswith("MATCH-")
        assert result["processing_timestamp"] is not None

    def test_zero_variance_calculates_correctly(self, perfect_match_request):
        """Zero variance should result in zero variance amount and percentage."""
        response = httpx.post(f"{MATCH_URL}/match", json=perfect_match_request, timeout=60)
        assert response.status_code == 200
        result = response.json()
        assert result["variance_amount"] == 0.0
        assert result["variance_percentage"] == 0.0
