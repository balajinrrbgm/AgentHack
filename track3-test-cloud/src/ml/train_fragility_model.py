"""
TestGen AI Sentinel — ML Model Training Script
Track 3: UiPath Test Cloud

Train the test fragility prediction model on historical execution data.

Usage:
    # Train on synthetic data (quickstart):
    python src/ml/train_fragility_model.py

    # Train on real historical data from UiPath Test Cloud export:
    python src/ml/train_fragility_model.py --historical-data data/test_history.csv

    # Full options:
    python src/ml/train_fragility_model.py \
        --historical-data data/test_history.csv \
        --output-dir models/ \
        --n-estimators 200 \
        --test-split 0.2 \
        --verbose
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    confusion_matrix,
    precision_recall_curve,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import joblib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Feature columns expected in the CSV
FEATURE_COLS = [
    "failure_rate_30d",
    "selector_stability",
    "exec_time_norm",
    "staleness",
    "deploy_corr",
    "page_load",
    "flakiness",
    "dom_depth_norm",
    "consec_fail_norm",
    "last_pass_penalty",
]

SELECTOR_STABILITY_MAP = {
    "DATA_TESTID": 5,
    "TEXT": 4,
    "CSS": 3,
    "XPATH": 2,
    "CLASS": 2,
    "ID": 1,
}


# ─────────────────────────────────────────────
# Data Loading & Preprocessing
# ─────────────────────────────────────────────

def load_csv_data(csv_path: str) -> pd.DataFrame:
    """
    Load and preprocess historical test execution data from UiPath Test Cloud export.

    Expected CSV columns (from Test Cloud export):
        test_id, test_name, selector_type, failure_count_30d, run_count_30d,
        avg_execution_time_ms, last_updated_date, deployment_failures_30d,
        has_page_load_wait, failure_count_7d, consecutive_failures,
        last_passed_date, dom_element_depth, is_fragile (label — 1/0 or True/False)
    """
    logger.info(f"Loading historical data from: {csv_path}")
    df = pd.read_csv(csv_path)

    logger.info(f"Loaded {len(df):,} test execution records")

    required = {"test_id", "failure_count_30d", "run_count_30d"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Derived features
    df["failure_rate_30d"] = df["failure_count_30d"] / df["run_count_30d"].clip(lower=1)
    df["selector_stability"] = (
        df["selector_type"].map(SELECTOR_STABILITY_MAP).fillna(2) / 5.0
    )
    df["exec_time_norm"] = (df["avg_execution_time_ms"] / 30000).clip(upper=1.0)

    if "last_updated_date" in df.columns:
        df["days_since_update"] = (
            pd.Timestamp.now() - pd.to_datetime(df["last_updated_date"])
        ).dt.days.clip(lower=0)
    else:
        df["days_since_update"] = 90
    df["staleness"] = (df["days_since_update"] / 365).clip(upper=1.0)

    if "deployment_failures_30d" in df.columns and "run_count_30d" in df.columns:
        df["deploy_corr"] = (df["deployment_failures_30d"] / df["run_count_30d"].clip(lower=1)).clip(upper=1.0)
    else:
        df["deploy_corr"] = 0.0

    df["page_load"] = df.get("has_page_load_wait", pd.Series(False)).astype(float)

    if "failure_count_7d" in df.columns:
        df["flakiness"] = (df["failure_count_7d"] / df["run_count_30d"].clip(lower=1) * 4).clip(upper=1.0)
    else:
        df["flakiness"] = df["failure_rate_30d"] * 0.5

    df["dom_depth_norm"] = (df.get("dom_element_depth", pd.Series(5)) / 20).clip(upper=1.0)
    df["consec_fail_norm"] = (
        (df.get("consecutive_failures", pd.Series(0)) * 15) / 50
    ).clip(upper=1.0)

    if "last_passed_date" in df.columns:
        df["last_pass_days"] = (
            pd.Timestamp.now() - pd.to_datetime(df["last_passed_date"])
        ).dt.days.fillna(30).clip(lower=0)
        df["last_pass_penalty"] = (df["last_pass_days"] / 30).clip(upper=1.0)
    else:
        df["last_pass_penalty"] = 0.0

    # Label: use provided 'is_fragile' column, or derive from failure_rate > 0.4
    if "is_fragile" in df.columns:
        df["fragile"] = df["is_fragile"].astype(int)
    else:
        logger.warning("No 'is_fragile' label column found — deriving from failure_rate_30d > 0.4")
        df["fragile"] = (df["failure_rate_30d"] > 0.4).astype(int)

    return df


def generate_synthetic_data(n_samples: int = 2000) -> pd.DataFrame:
    """Generate synthetic training data for quickstart demo."""
    logger.info(f"Generating {n_samples:,} synthetic training samples")
    np.random.seed(42)

    data = []
    for _ in range(n_samples):
        base = np.random.random()

        failure_rate = np.clip(base * 0.6 + np.random.normal(0, 0.1), 0, 1)
        selector_types = list(SELECTOR_STABILITY_MAP.keys())
        selector_weights = [0.1, 0.15, 0.15, 0.2, 0.2, 0.2]
        selector = np.random.choice(selector_types, p=selector_weights)
        selector_stability = SELECTOR_STABILITY_MAP[selector] / 5.0

        if base > 0.65:
            selector = np.random.choice(["ID", "XPATH"], p=[0.6, 0.4])
            selector_stability = SELECTOR_STABILITY_MAP[selector] / 5.0

        fragility_raw = (
            failure_rate * 0.3 +
            (1 - selector_stability) * 0.25 +
            min(np.random.lognormal(7, 1.5) / 30000, 1.0) * 0.1 +
            min(int(np.random.exponential(120)) / 365, 1.0) * 0.1 +
            np.clip(base * 0.5 + np.random.random() * 0.3, 0, 1) * 0.1 +
            float(np.random.random() > 0.6) * 0.05 +
            np.clip(base * 0.4 + np.random.random() * 0.2, 0, 1) * 0.05 +
            min(int(np.random.exponential(6)) / 20, 1.0) * 0.05
        )

        data.append({
            "failure_rate_30d": failure_rate,
            "selector_stability": selector_stability,
            "exec_time_norm": min(np.random.lognormal(7, 1.5) / 30000, 1.0),
            "staleness": min(int(np.random.exponential(120)) / 365, 1.0),
            "deploy_corr": np.clip(base * 0.5 + np.random.random() * 0.3, 0, 1),
            "page_load": float(np.random.random() > 0.6),
            "flakiness": np.clip(base * 0.4 + np.random.random() * 0.2, 0, 1),
            "dom_depth_norm": min(int(np.random.exponential(6)) / 20, 1.0),
            "consec_fail_norm": min(int(np.random.choice([0, 1, 2, 3, 5, 10],
                                                          p=[0.6, 0.15, 0.1, 0.07, 0.05, 0.03])) * 15 / 50, 1.0),
            "last_pass_penalty": 0.0,
            "fragile": int(fragility_raw > 0.45),
        })

    return pd.DataFrame(data)


# ─────────────────────────────────────────────
# Training
# ─────────────────────────────────────────────

def train(df: pd.DataFrame, n_estimators: int, test_split: float,
          output_dir: Path, verbose: bool) -> dict:
    """Train the gradient boosting fragility model and save artifacts."""

    X = df[FEATURE_COLS].values
    y = df["fragile"].values

    logger.info(f"Dataset: {len(X):,} samples | Fragile: {y.sum():,} ({y.mean():.1%}) | "
                f"Healthy: {(1-y).sum():,} ({(1-y).mean():.1%})")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_split, random_state=42, stratify=y
    )

    # Hyperparameter tuning with cross-validation
    if verbose:
        param_grid = {
            "clf__n_estimators": [100, 200],
            "clf__learning_rate": [0.05, 0.1],
            "clf__max_depth": [3, 4, 5],
        }
        logger.info("Running hyperparameter search (GridSearchCV)...")
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(random_state=42))
        ])
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        grid_search = GridSearchCV(pipeline, param_grid, cv=cv, scoring="roc_auc", n_jobs=-1, verbose=1)
        grid_search.fit(X_train, y_train)
        best_model = grid_search.best_estimator_
        logger.info(f"Best params: {grid_search.best_params_}")
        logger.info(f"Best CV AUC: {grid_search.best_score_:.4f}")
    else:
        logger.info(f"Training GradientBoostingClassifier (n_estimators={n_estimators})...")
        best_model = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(
                n_estimators=n_estimators,
                learning_rate=0.1,
                max_depth=4,
                random_state=42
            ))
        ])
        best_model.fit(X_train, y_train)

    # Evaluate
    y_pred = best_model.predict(X_test)
    y_proba = best_model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_proba)

    logger.info(f"\nTest Set AUC: {auc:.4f}")
    logger.info("\n" + classification_report(y_test, y_pred, target_names=["Healthy", "Fragile"]))

    cm = confusion_matrix(y_test, y_pred)
    logger.info(f"Confusion Matrix:\n{cm}")

    # Feature importance
    clf = best_model.named_steps["clf"]
    importances = dict(zip(FEATURE_COLS, clf.feature_importances_))
    sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    logger.info("\nFeature Importances:")
    for feat, imp in sorted_imp:
        logger.info(f"  {feat:30s}: {imp:.4f}")

    # Save artifacts
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "fragility_model.joblib"
    joblib.dump(best_model, model_path)
    logger.info(f"\nModel saved to: {model_path}")

    # Save metadata
    metadata = {
        "auc_roc": round(auc, 4),
        "n_samples": len(X),
        "n_fragile": int(y.sum()),
        "n_healthy": int((1 - y).sum()),
        "feature_columns": FEATURE_COLS,
        "feature_importances": {k: round(v, 4) for k, v in sorted_imp},
        "n_estimators": n_estimators,
        "model_path": str(model_path),
    }
    meta_path = output_dir / "model_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2))
    logger.info(f"Metadata saved to: {meta_path}")

    return metadata


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Train the TestGen AI Sentinel fragility prediction model"
    )
    parser.add_argument(
        "--historical-data",
        type=str,
        default=None,
        help="Path to CSV with historical test execution data (default: generate synthetic data)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="models",
        help="Directory to save model artifacts (default: models/)"
    )
    parser.add_argument(
        "--n-estimators",
        type=int,
        default=100,
        help="Number of gradient boosting trees (default: 100)"
    )
    parser.add_argument(
        "--test-split",
        type=float,
        default=0.2,
        help="Fraction of data to use for test evaluation (default: 0.2)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Run hyperparameter grid search (slower but better model)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.historical_data:
        df = load_csv_data(args.historical_data)
    else:
        logger.info("No historical data provided — using synthetic data for demo")
        df = generate_synthetic_data(n_samples=2000)

    output_dir = Path(args.output_dir)

    metadata = train(
        df=df,
        n_estimators=args.n_estimators,
        test_split=args.test_split,
        output_dir=output_dir,
        verbose=args.verbose,
    )

    logger.info("\n✅ Training complete!")
    logger.info(f"   AUC-ROC: {metadata['auc_roc']:.4f}")
    logger.info(f"   Model:   {metadata['model_path']}")
    logger.info(f"\nNow start the fragility model server:")
    logger.info(f"   uvicorn src.ml.fragility_model:app --port 8007")


if __name__ == "__main__":
    main()
