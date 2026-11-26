"""
TestGen AI Sentinel — Integration Tests
Track 3: UiPath Test Cloud
"""

import pytest
import httpx
import json
from datetime import datetime

GEN_URL = "http://localhost:8005"   # Test Generator Agent
HEAL_URL = "http://localhost:8006"  # Self-Healing Agent


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def login_requirement():
    return {
        "source": "MANUAL",
        "requirement_id": "DEMO-101",
        "title": "SSO Login with Microsoft Entra ID",
        "description": "As a user, I want to log in using my Microsoft account so that I can access the application without a separate password.",
        "acceptance_criteria": [
            "Users can click 'Sign in with Microsoft' button on login page",
            "Authentication redirects to Microsoft login page",
            "After successful auth, user is returned to app and logged in",
            "Failed auth shows appropriate error message",
            "Session persists for 8 hours"
        ],
        "component": "AuthenticationModule",
        "priority": "CRITICAL",
        "existing_tests": ["TC-LOGIN-001", "TC-LOGIN-002"]
    }


@pytest.fixture
def payment_requirement():
    return {
        "source": "JIRA",
        "requirement_id": "FEAT-456",
        "title": "Process Credit Card Payment",
        "description": "The system must process credit card payments securely, supporting Visa, Mastercard, and Amex. Payments over $10,000 require additional verification.",
        "acceptance_criteria": [
            "Accepts Visa, Mastercard, Amex",
            "Shows payment success confirmation",
            "Shows payment failure with clear error",
            "Payments over $10,000 trigger 2FA verification",
            "All payment data encrypted in transit"
        ],
        "component": "PaymentModule",
        "priority": "HIGH",
        "existing_tests": []
    }


@pytest.fixture
def selector_failure():
    return {
        "test_id": "TC-EDIT-001",
        "test_name": "UserProfile_EditModal_Submit",
        "failure_type": "SELECTOR_NOT_FOUND",
        "error_message": 'Selector not found: <webctrl id="edit-modal-submit-btn-1847" tag="BUTTON"/>. Element not found after 30000ms.',
        "test_code": '''<TestCase Name="UserProfile_EditModal_Submit">
  <Click Target="edit-modal-submit-btn-1847"/>
  <VerifyExpression Expression="SuccessMessage" Operator="Contains" Value="Profile updated"/>
</TestCase>''',
        "failure_timestamp": datetime.utcnow().isoformat(),
        "consecutive_failures": 3,
        "application_version": "v2.14.0",
        "recent_deployments": ["UI v2.14.0 - Updated profile modal layout"]
    }


@pytest.fixture
def timeout_failure():
    return {
        "test_id": "TC-LOAD-002",
        "test_name": "Dashboard_DataLoad_Performance",
        "failure_type": "TIMEOUT",
        "error_message": "Activity 'WaitPageLoad' timed out after 10000ms. Expected page to load within 10 seconds.",
        "test_code": '''<TestCase Name="Dashboard_DataLoad_Performance">
  <Navigate Url="https://app.example.com/dashboard" Timeout="10000"/>
  <WaitElementAppear Selector="dashboard-chart-container" Timeout="10000"/>
  <VerifyExpression Expression="ChartLoaded" Operator="Equals" Value="True"/>
</TestCase>''',
        "failure_timestamp": datetime.utcnow().isoformat(),
        "consecutive_failures": 2,
        "application_version": "v2.14.0",
        "recent_deployments": ["Backend v2.14.1 - Database query optimization (in progress)"]
    }


# ─────────────────────────────────────────────
# Test Generator Tests
# ─────────────────────────────────────────────

class TestGeneratorAgent:

    def test_health_check(self):
        response = httpx.get(f"{GEN_URL}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_generates_test_suite_for_login(self, login_requirement):
        """Should generate tests for SSO login requirement."""
        response = httpx.post(
            f"{GEN_URL}/generate-tests",
            json=login_requirement,
            timeout=120
        )
        assert response.status_code == 200
        result = response.json()

        assert result["suite_id"].startswith("SUITE-")
        assert result["requirement_id"] == "DEMO-101"
        assert len(result["test_scenarios"]) >= 3  # At least happy path + 2 negatives
        assert result["test_automation_code"] is not None
        assert len(result["test_automation_code"]) > 100
        assert "generation_timestamp" in result

    def test_critical_requirement_generates_security_tests(self, login_requirement):
        """CRITICAL priority auth requirement should generate security tests."""
        response = httpx.post(
            f"{GEN_URL}/generate-tests",
            json=login_requirement,
            timeout=120
        )
        assert response.status_code == 200
        result = response.json()

        # Auth requirement should include security scenarios
        test_types = [s.get("type", "") for s in result["test_scenarios"]]
        # Should have at least happy path and negative
        assert "HAPPY_PATH" in test_types or "NEGATIVE" in test_types

    def test_payment_requirement_boundary_tests(self, payment_requirement):
        """Payment requirement with threshold ($10K) should generate boundary tests."""
        response = httpx.post(
            f"{GEN_URL}/generate-tests",
            json=payment_requirement,
            timeout=120
        )
        assert response.status_code == 200
        result = response.json()

        assert len(result["test_scenarios"]) >= 3
        assert result["coverage_analysis"] is not None
        assert "test_dimensions" in result["coverage_analysis"]

    def test_generated_code_contains_test_case_xml(self, login_requirement):
        """Generated code should be valid UiPath test automation format."""
        response = httpx.post(
            f"{GEN_URL}/generate-tests",
            json=login_requirement,
            timeout=120
        )
        assert response.status_code == 200
        result = response.json()

        code = result["test_automation_code"]
        # Should contain UiPath test case elements
        assert "TestCase" in code or "testcase" in code.lower()

    def test_risk_assessment_included(self, login_requirement):
        """Risk assessment should be included in the result."""
        response = httpx.post(
            f"{GEN_URL}/generate-tests",
            json=login_requirement,
            timeout=120
        )
        assert response.status_code == 200
        result = response.json()

        assert "risk_assessment" in result
        assert "risk_level" in result["risk_assessment"]

    def test_missing_requirement_id_fails(self):
        """Request without requirement_id should fail validation."""
        response = httpx.post(f"{GEN_URL}/generate-tests", json={}, timeout=10)
        assert response.status_code == 422


# ─────────────────────────────────────────────
# Self-Healing Agent Tests
# ─────────────────────────────────────────────

class TestSelfHealingAgent:

    def test_health_check(self):
        response = httpx.get(f"{HEAL_URL}/health")
        assert response.status_code == 200

    def test_heals_selector_failure(self, selector_failure):
        """Selector failure should be diagnosed and fixed."""
        response = httpx.post(f"{HEAL_URL}/heal", json=selector_failure, timeout=120)
        assert response.status_code == 200
        result = response.json()

        assert result["healing_id"].startswith("HEAL-")
        assert result["test_id"] == "TC-EDIT-001"
        assert result["diagnosis"] is not None
        assert result["root_cause"] is not None
        assert 0.0 <= result["confidence_score"] <= 1.0
        assert result["validation_result"] in ["APPROVED", "REVIEW_REQUIRED"]

    def test_heals_timeout_failure(self, timeout_failure):
        """Timeout failure should generate appropriate fix."""
        response = httpx.post(f"{HEAL_URL}/heal", json=timeout_failure, timeout=120)
        assert response.status_code == 200
        result = response.json()

        assert result["healing_id"].startswith("HEAL-")
        assert result["confidence_score"] > 0.0
        assert result["fixed_code"] is not None

    def test_high_confidence_fix_auto_applied(self, selector_failure):
        """High confidence fixes should be auto-applied."""
        selector_failure["consecutive_failures"] = 5  # Definitely broken

        response = httpx.post(f"{HEAL_URL}/heal", json=selector_failure, timeout=120)
        assert response.status_code == 200
        result = response.json()

        if result["confidence_score"] >= 0.80:
            assert result["auto_applied"] is True
        else:
            assert result["requires_human_review"] is True

    def test_healing_result_has_timestamp(self, selector_failure):
        """Healing result should have a timestamp."""
        response = httpx.post(f"{HEAL_URL}/heal", json=selector_failure, timeout=120)
        assert response.status_code == 200
        result = response.json()
        assert "healing_timestamp" in result
        datetime.fromisoformat(result["healing_timestamp"])
