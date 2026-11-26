"""
MediClaim Guardian — End-to-End Integration Tests
Track 1: UiPath Maestro Case
"""

import pytest
import httpx
import json
from datetime import datetime

BASE_URL = "http://localhost:8001"  # Clinical Reasoning Agent
FRAUD_URL = "http://localhost:8002"  # Fraud Investigation Crew


# ─────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def standard_claim():
    return {
        "claim_id": "CLM-TEST-001",
        "patient_id": "PAT-12345",
        "procedure_codes": ["99213"],
        "diagnosis_codes": ["J18.9"],
        "provider_npi": "1234567891",
        "service_date": "2026-06-15",
        "place_of_service": "11",
        "units": 1,
        "billed_amount": 95.00,
        "clinical_notes": "Patient presenting with pneumonia, follow-up visit",
        "prior_auth_number": None
    }


@pytest.fixture
def complex_claim():
    return {
        "claim_id": "CLM-TEST-002",
        "patient_id": "PAT-99876",
        "procedure_codes": ["27447"],
        "diagnosis_codes": ["M17.11"],
        "provider_npi": "9876543210",
        "service_date": "2026-06-10",
        "place_of_service": "21",
        "units": 1,
        "billed_amount": 47000.00,
        "clinical_notes": "Patient with severe osteoarthritis, failed conservative treatment x18 months, x-ray confirms grade 4 cartilage loss",
        "prior_auth_number": "PA-2026-44721"
    }


@pytest.fixture
def suspicious_claim():
    return {
        "claim_id": "CLM-TEST-003",
        "patient_id": "PAT-55555",
        "procedure_codes": ["27447", "99285"],  # Knee replacement + ER visit — suspicious combo
        "diagnosis_codes": ["M54.5"],            # Low back pain — wrong diagnosis for knee replacement
        "provider_npi": "1111111111",
        "service_date": "2026-06-20",
        "place_of_service": "23",
        "units": 1,
        "billed_amount": 52000.00,
        "clinical_notes": None,                  # No clinical documentation
        "prior_auth_number": None
    }


# ─────────────────────────────────────────────
# Clinical Reasoning Agent Tests
# ─────────────────────────────────────────────

class TestClinicalTriageAgent:

    def test_health_check(self):
        """Agent should be healthy before running any tests."""
        response = httpx.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_standard_claim_triage(self, standard_claim):
        """Standard office visit should route to AUTO_APPROVE or STANDARD_REVIEW."""
        response = httpx.post(f"{BASE_URL}/triage", json=standard_claim, timeout=60)
        assert response.status_code == 200
        result = response.json()

        assert result["claim_id"] == "CLM-TEST-001"
        assert result["complexity_score"] <= 40  # Standard claim should be low complexity
        assert result["risk_tier"] in ["LOW", "MEDIUM"]
        assert result["recommended_path"] in ["AUTO_APPROVE", "STANDARD_REVIEW"]
        assert len(result["fraud_flags"]) == 0
        assert result["confidence"] >= 0.7

    def test_complex_claim_triage(self, complex_claim):
        """High-value knee replacement should score medium-high complexity."""
        response = httpx.post(f"{BASE_URL}/triage", json=complex_claim, timeout=60)
        assert response.status_code == 200
        result = response.json()

        assert result["claim_id"] == "CLM-TEST-002"
        assert result["complexity_score"] >= 50  # Complex claim
        assert result["recommended_path"] in ["STANDARD_REVIEW", "EXPERT_REVIEW"]
        # Should have prior auth noted
        assert result["confidence"] >= 0.6

    def test_suspicious_claim_flags_fraud(self, suspicious_claim):
        """Suspicious claim should trigger fraud investigation path."""
        response = httpx.post(f"{BASE_URL}/triage", json=suspicious_claim, timeout=60)
        assert response.status_code == 200
        result = response.json()

        assert result["claim_id"] == "CLM-TEST-003"
        # Should flag diagnosis-procedure mismatch
        assert len(result["clinical_concerns"]) > 0 or len(result["fraud_flags"]) > 0
        # Should NOT auto-approve a suspicious claim
        assert result["recommended_path"] != "AUTO_APPROVE"

    def test_claim_requires_claim_id(self):
        """Missing required fields should return 422."""
        response = httpx.post(f"{BASE_URL}/triage", json={}, timeout=10)
        assert response.status_code == 422

    def test_triage_response_has_timestamp(self, standard_claim):
        """Response should include a processing timestamp."""
        response = httpx.post(f"{BASE_URL}/triage", json=standard_claim, timeout=60)
        assert response.status_code == 200
        result = response.json()
        assert "processing_timestamp" in result
        # Timestamp should be valid ISO format
        datetime.fromisoformat(result["processing_timestamp"])

    def test_batch_triage(self, standard_claim, complex_claim):
        """Batch endpoint should process multiple claims."""
        response = httpx.post(
            f"{BASE_URL}/batch-triage",
            json=[standard_claim, complex_claim],
            timeout=120
        )
        assert response.status_code == 200
        result = response.json()
        assert "results" in result
        assert len(result["results"]) == 2

    def test_batch_triage_size_limit(self, standard_claim):
        """Batch triage should reject more than 50 claims."""
        batch = [standard_claim.copy() for _ in range(51)]
        for i, claim in enumerate(batch):
            claim["claim_id"] = f"CLM-BATCH-{i:03d}"

        response = httpx.post(f"{BASE_URL}/batch-triage", json=batch, timeout=10)
        assert response.status_code == 400


# ─────────────────────────────────────────────
# Fraud Investigation Tests
# ─────────────────────────────────────────────

class TestFraudInvestigationCrew:

    def test_fraud_agent_health(self):
        """Fraud investigation crew should be healthy."""
        response = httpx.get(f"{FRAUD_URL}/health")
        assert response.status_code == 200

    def test_standard_investigation(self, standard_claim):
        """Standard claim investigation should complete with recommendation."""
        investigation_request = {
            "claim_id": standard_claim["claim_id"],
            "triage_result": {
                "complexity_score": 25,
                "risk_tier": "LOW",
                "recommended_path": "STANDARD_REVIEW"
            },
            "claim_data": standard_claim,
            "investigation_type": "STANDARD"
        }

        response = httpx.post(f"{FRAUD_URL}/investigate", json=investigation_request, timeout=120)
        assert response.status_code == 200
        result = response.json()

        assert result["claim_id"] == standard_claim["claim_id"]
        assert result["overall_recommendation"] in ["APPROVE", "DENY", "ESCALATE", "REFER_FRAUD"]
        assert 0.0 <= result["confidence_score"] <= 1.0
        assert 0 <= result["fraud_risk_score"] <= 100
        assert len(result["key_findings"]) > 0
        assert result["investigation_timestamp"] is not None


# ─────────────────────────────────────────────
# Edge Case Tests
# ─────────────────────────────────────────────

class TestEdgeCases:

    def test_missing_clinical_notes(self, complex_claim):
        """Claim without clinical notes should still process."""
        complex_claim["clinical_notes"] = None
        response = httpx.post(f"{BASE_URL}/triage", json=complex_claim, timeout=60)
        assert response.status_code == 200

    def test_zero_billed_amount(self, standard_claim):
        """Zero billed amount should be handled gracefully."""
        standard_claim["billed_amount"] = 0.0
        response = httpx.post(f"{BASE_URL}/triage", json=standard_claim, timeout=60)
        # Should either succeed with a flag or return appropriate validation error
        assert response.status_code in [200, 422]

    def test_multiple_procedures(self, standard_claim):
        """Claim with multiple procedures should be handled."""
        standard_claim["procedure_codes"] = ["99213", "93000", "90834"]
        standard_claim["diagnosis_codes"] = ["J18.9", "I25.10", "F32.1"]
        response = httpx.post(f"{BASE_URL}/triage", json=standard_claim, timeout=60)
        assert response.status_code == 200
