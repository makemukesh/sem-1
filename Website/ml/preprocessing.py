"""
RainVision Preprocessing Module
Validates inputs against physical bounds and constructs leak-free 17-feature vectors.
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "temperature", "humidity", "pressure", "wind_speed",
    "rain_lag_1", "rain_lag_2", "rain_lag_3",
    "rain_roll_mean_7", "rain_roll_sum_7", "rain_roll_max_7", "rain_roll_mean_14",
    "temp_lag_1", "humidity_lag_1", "pressure_diff_1",
    "sin_day_of_year", "cos_day_of_year", "is_monsoon"
]

VALIDATION_BOUNDS = {
    "temperature": (-10.0, 60.0, "°C"),
    "humidity": (0.0, 100.0, "%"),
    "pressure": (850.0, 1100.0, "hPa"),
    "wind_speed": (0.0, 180.0, "km/h"),
    "previous_rainfall": (0.0, 500.0, "mm"),
    "rain_lag_1": (0.0, 500.0, "mm"),
    "rain_lag_2": (0.0, 500.0, "mm"),
    "rain_lag_3": (0.0, 500.0, "mm")
}


def validate_weather_inputs(inputs: Dict[str, Any]) -> Dict[str, float]:
    """
    Validate input weather values against physical thermodynamic boundaries.
    """
    required_core = ["temperature", "humidity", "pressure", "wind_speed"]
    for field in required_core:
        if field not in inputs:
            raise ValueError(f"Missing required meteorological input field: '{field}'")
        try:
            val = float(inputs[field])
            if np.isnan(val):
                raise ValueError()
        except (TypeError, ValueError):
            raise ValueError(f"Field '{field}' must be a valid numeric number.")

    validated = {}
    for key, (b_min, b_max, unit) in VALIDATION_BOUNDS.items():
        if key in inputs and inputs[key] is not None and inputs[key] != "":
            try:
                val = float(inputs[key])
            except (ValueError, TypeError):
                raise ValueError(f"Field '{key}' must be a valid number.")

            if val < b_min or val > b_max:
                raise ValueError(
                    f"Value for '{key}' ({val} {unit}) is out of physical boundaries ({b_min} to {b_max} {unit})."
                )
            validated[key] = val

    return validated


def prepare_features(inputs: Dict[str, Any]) -> pd.DataFrame:
    """
    Transform raw user inputs into the exact 17-feature input dataframe for the models.
    """
    validated = validate_weather_inputs(inputs)
    row = dict(validated)

    # Date handling
    date_val = inputs.get("date", None)
    if date_val:
        try:
            dt = pd.to_datetime(date_val)
            doy = dt.dayofyear
            month = dt.month
        except Exception:
            doy = int(inputs.get("day_of_year", 180))
            month = int(inputs.get("month", 7))
    else:
        doy = int(inputs.get("day_of_year", 180))
        month = int(inputs.get("month", 7))

    row["sin_day_of_year"] = np.sin(2 * np.pi * doy / 365.25)
    row["cos_day_of_year"] = np.cos(2 * np.pi * doy / 365.25)
    row["is_monsoon"] = 1.0 if month in [6, 7, 8, 9] else 0.0

    # Handle lag and previous rainfall
    prev_rain = float(inputs.get("previous_rainfall", inputs.get("rain_lag_1", 0.0)))
    row["rain_lag_1"] = prev_rain
    row["rain_lag_2"] = float(inputs.get("rain_lag_2", prev_rain))
    row["rain_lag_3"] = float(inputs.get("rain_lag_3", row["rain_lag_2"]))

    row["rain_roll_mean_7"] = float(inputs.get("rain_roll_mean_7", prev_rain))
    row["rain_roll_sum_7"] = float(inputs.get("rain_roll_sum_7", prev_rain * 7.0))
    row["rain_roll_max_7"] = float(inputs.get("rain_roll_max_7", prev_rain))
    row["rain_roll_mean_14"] = float(inputs.get("rain_roll_mean_14", row["rain_roll_mean_7"]))

    row["temp_lag_1"] = float(inputs.get("temp_lag_1", row["temperature"]))
    row["humidity_lag_1"] = float(inputs.get("humidity_lag_1", row["humidity"]))
    row["pressure_diff_1"] = float(inputs.get("pressure_diff_1", 0.0))

    # Form ordered dataframe
    feat_dict = {col: [row.get(col, 0.0)] for col in FEATURE_COLUMNS}
    return pd.DataFrame(feat_dict)

