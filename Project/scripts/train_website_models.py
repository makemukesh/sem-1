"""Train and publish RainVision models from the project workbook."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEBSITE_ROOT = PROJECT_ROOT.parent / "Website"
WORKBOOK_PATH = PROJECT_ROOT / "data" / "RainVision_Historical_1985_to_Today.xlsx"
MODEL_OUTPUT_DIRS = (
    PROJECT_ROOT / "models",
    WEBSITE_ROOT / "models",
)

for import_path in (PROJECT_ROOT, WEBSITE_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from ml.prediction import HurdleRainfallModel
from ml.ensemble import RainVisionEnsembleRegressor
from src.feature_engineering import build_complete_features, get_model_feature_columns
from src.redesigned_models import RedesignedEnsembleRegressor

setattr(sys.modules["__main__"], "RedesignedEnsembleRegressor", RedesignedEnsembleRegressor)


def _regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    clipped = np.clip(predicted, 0.0, None)
    mse = float(mean_squared_error(actual, clipped))
    return {
        "r2_score": round(float(r2_score(actual, clipped)), 4),
        "mae_mm": round(float(mean_absolute_error(actual, clipped)), 3),
        "rmse_mm": round(float(np.sqrt(mse)), 3),
    }


def main() -> None:
    if not WORKBOOK_PATH.exists():
        raise FileNotFoundError(f"RainVision training workbook not found: {WORKBOOK_PATH}")

    master = pd.read_excel(
        WORKBOOK_PATH,
        sheet_name="Rainfall_Data_1985_to_Today",
    )
    holdout = pd.read_excel(WORKBOOK_PATH, sheet_name="Heldout_Test_Data")
    master["date"] = pd.to_datetime(master["date"], errors="raise")
    holdout["date"] = pd.to_datetime(holdout["date"], errors="raise")
    master = master.sort_values("date").reset_index(drop=True)
    holdout = holdout.sort_values("date").reset_index(drop=True)

    if holdout.empty:
        raise ValueError("Heldout_Test_Data is empty; refusing to publish unvalidated models.")
    if holdout["date"].duplicated().any():
        raise ValueError("Heldout_Test_Data contains duplicate dates.")

    features = get_model_feature_columns()
    engineered = build_complete_features(master, drop_na=True)
    holdout_start = holdout["date"].min()
    train = engineered.loc[engineered["date"] < holdout_start].copy()

    missing = set(features + ["rainfall"]) - set(train.columns)
    missing.update(set(features + ["rainfall"]) - set(holdout.columns))
    if missing:
        raise ValueError(f"Training or holdout data is missing columns: {sorted(missing)}")
    if train.empty:
        raise ValueError("No training rows precede the held-out test period.")
    if train["date"].max() >= holdout_start:
        raise ValueError("Training data overlaps the held-out test period.")

    X_train = train[features]
    y_train = train["rainfall"].astype(float)
    X_test = holdout[features]
    y_test = holdout["rainfall"].to_numpy(dtype=float)

    model_specs = {
        "regression": (
            LinearRegression(),
            "Ordinary Least Squares",
        ),
        "random_forest": (
            RandomForestRegressor(
                n_estimators=150,
                max_depth=6,
                min_samples_split=2,
                random_state=42,
                n_jobs=-1,
            ),
            "Random Forest: 150 trees, max_depth=6",
        ),
        "gradient_boosting": (
            GradientBoostingRegressor(
                n_estimators=140,
                learning_rate=0.08,
                max_depth=5,
                subsample=0.85,
                random_state=42,
            ),
            "Gradient Boosting: 140 trees, learning_rate=0.08, max_depth=5",
        ),
        "hurdle": (
            HurdleRainfallModel(),
            "Two-stage Random Forest occurrence classifier and wet-day regressor",
        ),
    }

    artifact_names = {
        "ensemble": "ensemble_model.joblib",
        "regression": "regression_model.joblib",
        "random_forest": "random_forest_model.joblib",
        "gradient_boosting": "gradient_boosting_model.joblib",
        "hurdle": "hurdle_model.joblib",
    }
    metadata_models = {}
    trained_models = {}

    for key, (model, algorithm) in model_specs.items():
        started = time.perf_counter()
        model.fit(X_train, y_train)
        training_time = time.perf_counter() - started
        trained_models[key] = model
        metadata_models[key] = {
            "file": artifact_names[key],
            "algorithm": algorithm,
            "training_time_s": round(training_time, 4),
            "holdout_metrics": _regression_metrics(y_test, model.predict(X_test)),
        }

    ensemble_path = PROJECT_ROOT / "models" / "redesigned_v2" / "rainvision_regressor_redesigned.joblib"
    if not ensemble_path.exists():
        raise FileNotFoundError(f"Validated RainVision ensemble not found: {ensemble_path}")
    redesigned_ensemble = joblib.load(ensemble_path)
    ensemble = RainVisionEnsembleRegressor(
        redesigned_ensemble.rf,
        redesigned_ensemble.gb,
        rf_weight=redesigned_ensemble.rf_weight,
        gb_weight=redesigned_ensemble.gb_weight,
    )
    trained_models["ensemble"] = ensemble
    metadata_models["ensemble"] = {
        "file": artifact_names["ensemble"],
        "algorithm": "Random Forest (60%) + Gradient Boosting (40%)",
        "training_time_s": None,
        "holdout_metrics": _regression_metrics(y_test, ensemble.predict(X_test)),
    }

    metadata = {
        "project": "RainVision",
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_file": str(WORKBOOK_PATH.relative_to(PROJECT_ROOT)),
        "training_records": int(len(train)),
        "training_date_range": [
            train["date"].min().date().isoformat(),
            train["date"].max().date().isoformat(),
        ],
        "holdout_records": int(len(holdout)),
        "holdout_date_range": [
            holdout["date"].min().date().isoformat(),
            holdout["date"].max().date().isoformat(),
        ],
        "feature_columns": features,
        "models": metadata_models,
    }

    for output_dir in MODEL_OUTPUT_DIRS:
        output_dir.mkdir(parents=True, exist_ok=True)
        for key, model in trained_models.items():
            joblib.dump(model, output_dir / artifact_names[key])
        metadata_path = output_dir / "model_metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(json.dumps(metadata, indent=2))
    print("Trained models were saved to:")
    for output_dir in MODEL_OUTPUT_DIRS:
        print(f"  {output_dir}")


if __name__ == "__main__":
    main()
