"""
RainVision Model Evaluation Module
Evaluates 4 Machine Learning Models on held-out test dataset (test.csv):
  1. Linear Regression (OLS)
  2. Random Forest Regressor
  3. Gradient Boosting Regressor
  4. Two-Stage Meteorological Hurdle Model
Calculates genuine R², MAE, RMSE, MSE, and latency.
"""

from pathlib import Path
import json
from typing import Dict, Any
import time
import numpy as np
import pandas as pd
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from ml.prediction import load_models
from ml.preprocessing import FEATURE_COLUMNS


def evaluate_models(models_dir: Path, test_csv_path: Path) -> Dict[str, Any]:
    models = load_models(models_dir)

    if not test_csv_path.exists():
        raise FileNotFoundError(f"Test dataset not found at {test_csv_path}")

    if test_csv_path.suffix.lower() == ".xlsx":
        test_df = pd.read_excel(test_csv_path, sheet_name="Heldout_Test_Data")
    else:
        test_df = pd.read_csv(test_csv_path)
    missing_columns = set(FEATURE_COLUMNS + ["rainfall"]) - set(test_df.columns)
    if missing_columns:
        raise ValueError(f"Holdout dataset is missing required columns: {sorted(missing_columns)}")

    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df["rainfall"].values

    metadata_path = models_dir / "model_metadata.json"
    metadata = {}
    if metadata_path.exists():
        with metadata_path.open("r", encoding="utf-8") as metadata_file:
            metadata = json.load(metadata_file)
    training_metadata = metadata.get("models", {})

    model_info = {
        "ensemble": (
            "RainVision Blended Ensemble Regressor",
            "Random Forest (60%) + Gradient Boosting (40%)"
        ),
        "random_forest": (
            "Random Forest Regressor",
            "150 Decision Trees, max_depth=6, min_samples_split=2"
        ),
        "gradient_boosting": (
            "Gradient Boosting Regressor",
            "140 Sequential Boosted Trees, lr=0.08, max_depth=5"
        ),
        "hurdle": (
            "Two-Stage Hurdle Model",
            "Stage 1: Rain-occurrence classifier + Stage 2: wet-day severity regressor"
        ),
        "regression": (
            "Linear Regression (OLS)",
            "Ordinary Least Squares with non-negative projection"
        )
    }
    predictions = {}
    model_metrics = {}
    for model_key, model in models.items():
        if model_key not in model_info:
            continue

        started = time.perf_counter()
        predictions[model_key] = np.clip(model.predict(X_test), 0.0, None)
        inference_ms = (time.perf_counter() - started) * 1000

        prediction = predictions[model_key]
        mse = float(mean_squared_error(y_test, prediction))
        training_details = training_metadata.get(model_key, {})
        name, algorithm = model_info[model_key]
        model_metrics[model_key] = {
            "name": name,
            "algorithm": training_details.get("algorithm", algorithm),
            "r2_score": round(float(r2_score(y_test, prediction)), 4),
            "mae_mm": round(float(mean_absolute_error(y_test, prediction)), 3),
            "rmse_mm": round(float(np.sqrt(mse)), 3),
            "mse_mm2": round(mse, 3),
            "training_time_s": training_details.get("training_time_s"),
            "inference_time_ms": round(inference_ms, 2)
        }

    if "regression" not in predictions or "random_forest" not in predictions:
        raise FileNotFoundError("Linear Regression and Random Forest models are required for evaluation.")

    # Scatter points sample (40 points across test timeline)
    scatter_sample = []
    step = max(1, len(test_df) // 40)
    for i in range(0, len(test_df), step):
        date_str = str(test_df["date"].iloc[i]) if "date" in test_df.columns else f"Day {i+1}"
        actual = round(float(y_test[i]), 2)
        lr_val = round(float(predictions["regression"][i]), 2)
        rf_val = round(float(predictions["random_forest"][i]), 2)
        scatter_sample.append({
            "index": i,
            "date": date_str[-5:] if len(date_str) >= 5 else date_str,
            "full_date": date_str,
            "actual": actual,
            "regression": lr_val,
            "ensemble": round(float(predictions["ensemble"][i]), 2) if "ensemble" in predictions else None,
            "random_forest": rf_val,
            "gradient_boosting": round(float(predictions["gradient_boosting"][i]), 2) if "gradient_boosting" in predictions else None,
            "hurdle": round(float(predictions["hurdle"][i]), 2) if "hurdle" in predictions else None,
            "diff": round(abs(lr_val - rf_val), 2)
        })

    sample_predictions = [
        {
            "actual_mm": sample["actual"],
            "ensemble_predicted_mm": sample["ensemble"],
            "rf_predicted_mm": sample["random_forest"],
            "reg_predicted_mm": sample["regression"]
        }
        for sample in scatter_sample
    ]

    best_r2_key = max(model_metrics, key=lambda key: model_metrics[key]["r2_score"])
    lowest_mae_key = min(model_metrics, key=lambda key: model_metrics[key]["mae_mm"])
    inference_times = {
        key: value["inference_time_ms"]
        for key, value in model_metrics.items()
        if value["inference_time_ms"] is not None
    }
    dry_mask = y_test <= 0.05
    dry_day_false_rain_rates = {
        key: float(np.mean(prediction[dry_mask] > 0.05) * 100)
        for key, prediction in predictions.items()
        if np.any(dry_mask)
    }
    summary = {
        "higher_r2": f"{model_metrics[best_r2_key]['name']} ({model_metrics[best_r2_key]['r2_score']:.4f})",
        "lowest_mae": f"{model_metrics[lowest_mae_key]['name']} ({model_metrics[lowest_mae_key]['mae_mm']:.3f} mm)",
        "best_zero_precipitation": (
            f"{model_metrics[min(dry_day_false_rain_rates, key=dry_day_false_rain_rates.get)]['name']} "
            f"({min(dry_day_false_rain_rates.values()):.1f}% false rain on dry days)"
            if dry_day_false_rain_rates else "No dry holdout observations"
        ),
        "fastest_inference": (
            f"{model_metrics[min(inference_times, key=inference_times.get)]['name']} "
            f"({min(inference_times.values()):.2f} ms)"
            if inference_times else "Unavailable"
        )
    }

    return {
        "test_records_count": len(test_df),
        "test_date_coverage": f"{test_df['date'].min()} to {test_df['date'].max()}" if "date" in test_df.columns else "Held-out test set",
        "models": model_metrics,
        "scatter_sample": scatter_sample,
        "sample_predictions": sample_predictions,
        "comparison_summary": summary
    }
