"""
RainVision Production Inference Pipeline
Handles model loading, input validation with meteorological domain rules,
feature transformation, multi-task inference, uncertainty estimation,
and weather advisory generation.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import json
import joblib
import numpy as np
import pandas as pd


VALIDATION_BOUNDS = {
    "temperature": (-10.0, 60.0, "°C"),
    "humidity": (0.0, 100.0, "%"),
    "pressure": (850.0, 1100.0, "hPa"),
    "wind_speed": (0.0, 180.0, "km/h"),
    "rain_lag_1": (0.0, 500.0, "mm"),
    "rain_lag_2": (0.0, 500.0, "mm"),
    "rain_lag_3": (0.0, 500.0, "mm"),
    "rain_roll_mean_7": (0.0, 500.0, "mm"),
    "rain_roll_sum_7": (0.0, 3000.0, "mm"),
    "rain_roll_max_7": (0.0, 500.0, "mm"),
    "rain_roll_mean_14": (0.0, 500.0, "mm"),
    "temp_lag_1": (-10.0, 60.0, "°C"),
    "humidity_lag_1": (0.0, 100.0, "%"),
    "pressure_diff_1": (-50.0, 50.0, "hPa"),
}


def load_rainvision_models(models_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Load serialized RainVision regressor, classifier, and metadata from disk.
    """
    if models_dir is None:
        from src.data_processing import get_project_root
        models_dir = get_project_root() / "models"
    else:
        models_dir = Path(models_dir)

    reg_path = models_dir / "rainvision_regressor.joblib"
    clf_path = models_dir / "rainvision_classifier.joblib"
    meta_path = models_dir / "model_metadata.json"

    if not reg_path.exists():
        raise FileNotFoundError(f"Regressor model file not found at {reg_path}")
    if not clf_path.exists():
        raise FileNotFoundError(f"Classifier model file not found at {clf_path}")

    regressor = joblib.load(reg_path)
    classifier = joblib.load(clf_path)

    metadata = {}
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

    return {
        "regressor": regressor,
        "classifier": classifier,
        "metadata": metadata
    }


def validate_weather_inputs(inputs: Dict[str, Any]) -> Dict[str, float]:
    """
    Validate raw input weather values against physical meteorological boundaries.
    Raises ValueError with actionable error message if out-of-bounds or missing.
    """
    required_core = ["temperature", "humidity", "pressure", "wind_speed"]
    for field in required_core:
        if field not in inputs:
            raise ValueError(f"Missing required meteorological input field: '{field}'")
        val = inputs[field]
        if val is None or not isinstance(val, (int, float)) or np.isnan(val):
            raise ValueError(f"Field '{field}' must be a valid numeric value, received: {val}")

    validated = {}
    for key, (b_min, b_max, unit) in VALIDATION_BOUNDS.items():
        if key in inputs:
            val = float(inputs[key])
            if val < b_min or val > b_max:
                raise ValueError(
                    f"Meteorological value out of physical bounds for '{key}': {val} {unit}. "
                    f"Expected valid physical range between {b_min} and {b_max} {unit}."
                )
            validated[key] = val

    return validated


def prepare_prediction_features(
    raw_inputs: Dict[str, Any],
    feature_names: List[str]
) -> pd.DataFrame:
    """
    Transform raw user weather observations into the exact ordered feature vector
    expected by the trained models.
    """
    val_inputs = validate_weather_inputs(raw_inputs)
    row = dict(val_inputs)

    # Date handling and calendar features
    date_val = raw_inputs.get("date", None)
    if date_val is not None:
        dt = pd.to_datetime(date_val)
        doy = dt.dayofyear
        month = dt.month
    else:
        # Default or provided day_of_year
        doy = int(raw_inputs.get("day_of_year", 180))
        month = int(raw_inputs.get("month", 7))

    row["sin_day_of_year"] = np.sin(2 * np.pi * doy / 365.25)
    row["cos_day_of_year"] = np.cos(2 * np.pi * doy / 365.25)
    row["is_monsoon"] = 1 if month in [6, 7, 8, 9] else 0

    # Fallbacks for lag features if not explicitly supplied
    if "rain_lag_1" not in row:
        row["rain_lag_1"] = float(raw_inputs.get("previous_rainfall", 0.0))
    if "rain_lag_2" not in row:
        row["rain_lag_2"] = row["rain_lag_1"]
    if "rain_lag_3" not in row:
        row["rain_lag_3"] = row["rain_lag_2"]

    if "rain_roll_mean_7" not in row:
        row["rain_roll_mean_7"] = row["rain_lag_1"]
    if "rain_roll_sum_7" not in row:
        row["rain_roll_sum_7"] = row["rain_lag_1"] * 7.0
    if "rain_roll_max_7" not in row:
        row["rain_roll_max_7"] = row["rain_lag_1"]
    if "rain_roll_mean_14" not in row:
        row["rain_roll_mean_14"] = row["rain_roll_mean_7"]

    if "temp_lag_1" not in row:
        row["temp_lag_1"] = row["temperature"]
    if "humidity_lag_1" not in row:
        row["humidity_lag_1"] = row["humidity"]
    if "pressure_diff_1" not in row:
        row["pressure_diff_1"] = 0.0

    # Ensure all feature columns exist in exact training order
    feat_dict = {col: [row.get(col, 0.0)] for col in feature_names}
    return pd.DataFrame(feat_dict)


def predict_rainfall_amount(regressor: Any, features_df: pd.DataFrame) -> float:
    """
    Predict continuous rainfall amount in millimeters, clipped at 0.0 mm.
    """
    raw_pred = float(regressor.predict(features_df)[0])
    return round(max(0.0, raw_pred), 2)


def predict_rainfall_category(classifier: Any, features_df: pd.DataFrame) -> str:
    """
    Predict rainfall intensity category ('No Rain', 'Light', 'Moderate', 'Heavy').
    """
    return str(classifier.predict(features_df)[0])


def generate_weather_advisory(amount_mm: float, category: str) -> str:
    """
    Generate meteorological public safety advisory based on predicted rainfall.
    """
    if category == "No Rain" or amount_mm <= 0.05:
        return "Dry conditions expected. Normal outdoor activities and agricultural operations may proceed."
    elif category == "Light" or amount_mm <= 2.5:
        return "Light showers anticipated. Mild dampness; carry an umbrella if traveling."
    elif category == "Moderate" or amount_mm <= 15.0:
        return "Moderate rainfall predicted. Potential water accumulation in low-lying spots. Drive with caution."
    else:
        return "HEAVY RAINFALL WARNING: Significant precipitation (>15 mm) expected. High risk of localized urban waterlogging and traffic disruption."


def predict_weather(
    regressor: Any,
    classifier: Any,
    raw_inputs: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Execute end-to-end multi-task weather prediction:
    1. Validates inputs
    2. Builds features
    3. Predicts continuous amount (mm)
    4. Predicts categorical intensity
    5. Formulates public advisory
    """
    if metadata and "features" in metadata:
        features_list = metadata["features"]
    else:
        from src.feature_engineering import get_model_feature_columns
        features_list = get_model_feature_columns()

    X_feat = prepare_prediction_features(raw_inputs, features_list)

    # 1. Classification prediction (intensity tier)
    category = str(classifier.predict(X_feat)[0])

    # 2. Regression prediction (amount in mm)
    raw_amount = float(regressor.predict(X_feat)[0])
    amount_mm = round(max(0.0, raw_amount), 2)

    # Meteorological consistency gating (Two-Stage Hurdle formulation):
    # If the atmospheric classifier predicts 'No Rain' (e.g. humidity < 45% in dry season),
    # clamp quantitative precipitation to 0.0 mm (dry / trace) to prevent MSE penalty artifacts
    if category == "No Rain" and amount_mm < 15.0:
        amount_mm = 0.0

    advisory = generate_weather_advisory(amount_mm, category)

    return {
        "predicted_rainfall_mm": amount_mm,
        "predicted_category": category,
        "advisory": advisory,
        "input_summary": {
            "temperature_c": raw_inputs.get("temperature"),
            "humidity_percent": raw_inputs.get("humidity"),
            "pressure_hpa": raw_inputs.get("pressure"),
            "wind_speed_kmh": raw_inputs.get("wind_speed"),
            "date": str(raw_inputs.get("date", "N/A"))
        },
        "model_version": metadata.get("version", "1.0.0") if metadata else "1.0.0"
    }
