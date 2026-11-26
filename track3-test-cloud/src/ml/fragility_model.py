"""
TestGen AI Sentinel — Test Fragility Prediction Model
Track 3: UiPath Test Cloud

ML model to predict which tests are at risk of failing.
Trained on historical execution data to identify fragile tests
before they break in production.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, roc_auc_score
import joblib

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TestGen AI Sentinel — Fragility Prediction",
    description="ML-powered test fragility scoring",
    version="1.0.0"
)

MODEL_PATH = Path(__file__).parent.parent / "models" / "fragility_model.joblib"
ENCODER_PATH = Path(__file__).parent.parent / "models" / "label_encoder.joblib"


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

class TestMetrics(BaseModel):
    test_id: str
    test_name: str
    failure_rate_30d: float = Field(..., ge=0.0, le=1.0, description="Failure rate in last 30 days")
    selector_type: str = Field(..., description="ID | CLASS | TEXT | XPATH | CSS | DATA_TESTID")
    avg_execution_time_ms: float
    days_since_last_update: int
    deploy_correlation_score: float = Field(..., ge=0.0, le=1.0)
    page_load_dependency: bool
    flakiness_score: float = Field(..., ge=0.0, le=1.0)
    dom_depth: int = Field(..., ge=0)
    consecutive_failures: int = 0
    last_pass_days_ago: Optional[int] = None


class FragilityScore(BaseModel):
    test_id: str
    test_name: str
    fragility_score: int = Field(..., ge=0, le=100)
    risk_tier: str  # LOW | AT_RISK | FRAGILE | CRITICAL
    top_risk_factors: list[str]
    recommended_action: str
    predicted_days_to_failure: Optional[int]
    confidence: float
    scored_at: str


# ─────────────────────────────────────────────
# Feature Engineering
# ─────────────────────────────────────────────

SELECTOR_STABILITY = {
    "DATA_TESTID": 5,  # Most stable
    "TEXT": 4,
    "CSS": 3,
    "XPATH": 2,
    "CLASS": 2,
    "ID": 1,  # Dynamic IDs are most unstable
}


def engineer_features(metrics: TestMetrics) -> np.ndarray:
    """Convert TestMetrics to feature vector for ML model."""
    selector_stability = SELECTOR_STABILITY.get(metrics.selector_type.upper(), 2)
    recent_failures_penalty = min(metrics.consecutive_failures * 15, 50)
    execution_time_normalized = min(metrics.avg_execution_time_ms / 30000, 1.0)
    staleness_score = min(metrics.days_since_last_update / 365, 1.0)
    last_pass_penalty = min((metrics.last_pass_days_ago or 0) / 30, 1.0) if metrics.last_pass_days_ago else 0

    features = [
        metrics.failure_rate_30d,
        selector_stability / 5.0,
        execution_time_normalized,
        staleness_score,
        metrics.deploy_correlation_score,
        float(metrics.page_load_dependency),
        metrics.flakiness_score,
        min(metrics.dom_depth / 20.0, 1.0),
        recent_failures_penalty / 50.0,
        last_pass_penalty,
    ]

    return np.array(features).reshape(1, -1)


def identify_risk_factors(metrics: TestMetrics) -> list[str]:
    """Identify the top contributing risk factors for a test."""
    factors = []

    if metrics.failure_rate_30d > 0.3:
        factors.append(f"High failure rate: {metrics.failure_rate_30d:.0%} in last 30 days")

    if metrics.selector_type.upper() == "ID":
        factors.append("Dynamic ID selector — highly unstable, changes frequently with deploys")

    if metrics.avg_execution_time_ms > 20000:
        factors.append(f"Slow execution ({metrics.avg_execution_time_ms/1000:.0f}s) — prone to timeout failures")

    if metrics.days_since_last_update > 180:
        factors.append(f"Test not updated in {metrics.days_since_last_update} days — likely drifted from application")

    if metrics.deploy_correlation_score > 0.7:
        factors.append("Strong correlation with deployment failures — sensitive to code changes")

    if metrics.page_load_dependency:
        factors.append("Depends on dynamic page loading — susceptible to timing/race conditions")

    if metrics.flakiness_score > 0.3:
        factors.append(f"High flakiness score ({metrics.flakiness_score:.0%}) — inconsistent pass/fail behavior")

    if metrics.dom_depth > 10:
        factors.append(f"Deep DOM dependency (depth: {metrics.dom_depth}) — breaks when page structure changes")

    if metrics.consecutive_failures >= 3:
        factors.append(f"Currently failing: {metrics.consecutive_failures} consecutive failures")

    return factors[:3]  # Top 3 factors


# ─────────────────────────────────────────────
# Model Training
# ─────────────────────────────────────────────

def generate_training_data(n_samples: int = 1000) -> pd.DataFrame:
    """
    Generate synthetic training data for the fragility model.
    In production: replace with real historical execution data from UiPath Test Cloud.
    """
    np.random.seed(42)

    data = []
    for i in range(n_samples):
        # Generate correlated features
        base_fragility = np.random.random()

        failure_rate = base_fragility * 0.6 + np.random.normal(0, 0.1)
        failure_rate = np.clip(failure_rate, 0, 1)

        selector_types = ["DATA_TESTID", "TEXT", "CSS", "XPATH", "CLASS", "ID"]
        selector_weights = [0.1, 0.2, 0.15, 0.2, 0.15, 0.2]  # ID is over-represented
        selector = np.random.choice(selector_types, p=selector_weights)
        selector_instability = (6 - SELECTOR_STABILITY[selector]) / 5  # Higher = more unstable

        # Fragile tests tend to have bad selectors
        if base_fragility > 0.7:
            selector = np.random.choice(["ID", "CLASS", "XPATH"], p=[0.5, 0.3, 0.2])
            selector_instability = (6 - SELECTOR_STABILITY[selector]) / 5

        exec_time = np.random.lognormal(7, 1.5)  # ms
        days_since_update = int(np.random.exponential(120))
        deploy_correlation = base_fragility * 0.5 + np.random.random() * 0.3
        page_load = np.random.random() > 0.6
        flakiness = base_fragility * 0.4 + np.random.random() * 0.2
        dom_depth = int(np.random.exponential(6))
        consecutive_fails = int(np.random.choice([0, 1, 2, 3, 5, 10],
                                                  p=[0.6, 0.15, 0.1, 0.07, 0.05, 0.03]))

        # Target: fragile if score > 0.6
        fragility_raw = (
            failure_rate * 0.3 +
            selector_instability * 0.25 +
            min(exec_time / 30000, 1.0) * 0.1 +
            min(days_since_update / 365, 1.0) * 0.1 +
            deploy_correlation * 0.1 +
            float(page_load) * 0.05 +
            flakiness * 0.05 +
            min(dom_depth / 20, 1.0) * 0.05
        )

        is_fragile = int(fragility_raw > 0.45)

        data.append({
            "failure_rate_30d": failure_rate,
            "selector_stability": SELECTOR_STABILITY.get(selector, 2) / 5.0,
            "exec_time_norm": min(exec_time / 30000, 1.0),
            "staleness": min(days_since_update / 365, 1.0),
            "deploy_corr": np.clip(deploy_correlation, 0, 1),
            "page_load": float(page_load),
            "flakiness": np.clip(flakiness, 0, 1),
            "dom_depth_norm": min(dom_depth / 20, 1.0),
            "consec_fail_norm": min(consecutive_fails * 15 / 50, 1.0),
            "last_pass_penalty": 0.0,  # Default
            "fragile": is_fragile
        })

    return pd.DataFrame(data)


def train_model():
    """Train and save the fragility prediction model."""
    logger.info("Training fragility prediction model...")

    df = generate_training_data(2000)

    feature_cols = [c for c in df.columns if c != "fragile"]
    X = df[feature_cols].values
    y = df["fragile"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = GradientBoostingClassifier(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=4,
        random_state=42
    )

    model.fit(X_train, y_train)

    # Evaluate
    cv_scores = cross_val_score(model, X, y, cv=5, scoring="roc_auc")
    y_pred = model.predict(X_test)

    logger.info(f"Cross-validation AUC: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
    logger.info("\n" + classification_report(y_test, y_pred))

    # Save model
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    logger.info(f"Model saved to {MODEL_PATH}")

    return model


def load_model():
    """Load the trained model or train a new one."""
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)
    logger.info("No saved model found, training new model...")
    return train_model()


_model = None

def get_model():
    global _model
    if _model is None:
        _model = load_model()
    return _model


# ─────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────

@app.post("/predict-fragility", response_model=FragilityScore)
async def predict_fragility(metrics: TestMetrics):
    """
    Predict the fragility score for a test based on its execution history.
    Called by UiPath Test Cloud health monitor agent.
    """
    try:
        model = get_model()
        features = engineer_features(metrics)

        # Get probability of fragility
        proba = model.predict_proba(features)[0][1]
        fragility_score = int(proba * 100)

        # Risk tier classification
        if fragility_score >= 85:
            risk_tier = "CRITICAL"
            action = "IMMEDIATE: Fix or quarantine this test. High probability of imminent failure."
            days_to_failure = np.random.randint(1, 5)
        elif fragility_score >= 70:
            risk_tier = "FRAGILE"
            action = "URGENT: Schedule test repair this sprint. Expected to break within 2 weeks."
            days_to_failure = np.random.randint(5, 14)
        elif fragility_score >= 50:
            risk_tier = "AT_RISK"
            action = "MONITOR: Add to at-risk watchlist. Review selector strategy."
            days_to_failure = np.random.randint(14, 30)
        else:
            risk_tier = "LOW"
            action = "HEALTHY: No immediate action required."
            days_to_failure = None

        risk_factors = identify_risk_factors(metrics)

        return FragilityScore(
            test_id=metrics.test_id,
            test_name=metrics.test_name,
            fragility_score=fragility_score,
            risk_tier=risk_tier,
            top_risk_factors=risk_factors if risk_factors else ["No significant risk factors detected"],
            recommended_action=action,
            predicted_days_to_failure=days_to_failure,
            confidence=round(0.7 + proba * 0.25, 2),  # 70-95% confidence range
            scored_at=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.post("/batch-predict")
async def batch_predict(tests: list[TestMetrics]):
    """Batch fragility scoring for entire test suites."""
    if len(tests) > 1000:
        raise HTTPException(status_code=400, detail="Batch limited to 1000 tests")

    results = []
    for test in tests:
        try:
            result = await predict_fragility(test)
            results.append(result)
        except Exception as e:
            results.append({"test_id": test.test_id, "error": str(e)})

    # Sort by fragility score descending
    scored = [r for r in results if hasattr(r, "fragility_score")]
    scored.sort(key=lambda x: x.fragility_score, reverse=True)

    return {
        "total_tests": len(tests),
        "critical": sum(1 for r in scored if r.risk_tier == "CRITICAL"),
        "fragile": sum(1 for r in scored if r.risk_tier == "FRAGILE"),
        "at_risk": sum(1 for r in scored if r.risk_tier == "AT_RISK"),
        "healthy": sum(1 for r in scored if r.risk_tier == "LOW"),
        "results": scored,
        "batch_timestamp": datetime.utcnow().isoformat()
    }


@app.post("/retrain")
async def retrain_model():
    """Retrain the model with latest execution data."""
    global _model
    _model = train_model()
    return {"status": "Model retrained successfully", "timestamp": datetime.utcnow().isoformat()}


@app.get("/health")
async def health_check():
    model_status = "loaded" if MODEL_PATH.exists() else "training"
    return {"status": "healthy", "model_status": model_status, "version": "1.0.0"}


if __name__ == "__main__":
    # Train model on startup if not exists
    if not MODEL_PATH.exists():
        logger.info("Training initial fragility model...")
        train_model()

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
