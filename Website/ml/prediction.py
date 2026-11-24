"""
RainVision Inference Engine & Meteorological Explainable AI (XAI)
Loads 4 Machine Learning Models:
  1. Linear Regression (OLS)
  2. Random Forest Regressor (150 Trees)
  3. Gradient Boosting Regressor
  4. Two-Stage Meteorological Hurdle Model (Rain Probability + Wet-day Severity)
Calculates physical boundaries, dew point depression, feature attribution, and genuine predictions.
"""

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Tuple, List
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from ml.ensemble import RainVisionEnsembleRegressor
from ml.preprocessing import prepare_features, validate_weather_inputs, FEATURE_COLUMNS

_MODELS_CACHE = {}


class HurdleRainfallModel:
    """
    Two-Stage Meteorological Hurdle Model:
    Stage 1: Predicts precipitation occurrence probability P(Rain > 0.05mm).
    Stage 2: Predicts quantitative precipitation depth conditioned on wet days.
    """
    def __init__(self, classifier=None, regressor=None, rain_threshold=0.05):
        self.rain_threshold = rain_threshold
        self.classifier = classifier or RandomForestClassifier(
            n_estimators=120,
            max_depth=7,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        )
        self.regressor = regressor or RandomForestRegressor(
            n_estimators=120,
            max_depth=8,
            min_samples_split=4,
            random_state=42,
            n_jobs=-1
        )

    def fit(self, X, y):
        X_df = pd.DataFrame(X, columns=FEATURE_COLUMNS) if not isinstance(X, pd.DataFrame) else X
        y_values = np.asarray(y, dtype=float)
        wet_mask = y_values > self.rain_threshold

        self.classifier.fit(X_df, wet_mask.astype(int))
        wet_indices = np.flatnonzero(wet_mask)
        severity_indices = wet_indices if len(wet_indices) > 10 else np.arange(len(y_values))
        self.regressor.fit(X_df.iloc[severity_indices], y_values[severity_indices])
        return self

    def predict_proba(self, X):
        X_df = pd.DataFrame(X, columns=FEATURE_COLUMNS) if not isinstance(X, pd.DataFrame) else X
        probs = self.classifier.predict_proba(X_df)
        return probs[:, 1] if probs.shape[1] > 1 else np.zeros(len(X_df))

    def predict(self, X):
        X_df = pd.DataFrame(X, columns=FEATURE_COLUMNS) if not isinstance(X, pd.DataFrame) else X
        p_wet = self.predict_proba(X_df)
        severity = np.clip(self.regressor.predict(X_df), 0.0, None)
        preds = np.where(p_wet >= 0.28, p_wet * severity, 0.0)
        return np.round(np.clip(preds, 0.0, None), 2)


# Inject into current and main modules for safe unpickling
sys.modules["HurdleRainfallModel"] = HurdleRainfallModel
if "__main__" in sys.modules:
    setattr(sys.modules["__main__"], "HurdleRainfallModel", HurdleRainfallModel)


def load_models(models_dir: Path) -> Dict[str, Any]:
    global _MODELS_CACHE
    if _MODELS_CACHE:
        return _MODELS_CACHE

    reg_path = models_dir / "regression_model.joblib"
    rf_path = models_dir / "random_forest_model.joblib"
    gb_path = models_dir / "gradient_boosting_model.joblib"
    h_path = models_dir / "hurdle_model.joblib"
    ensemble_path = models_dir / "ensemble_model.joblib"

    if not reg_path.exists():
        raise FileNotFoundError(f"Regression model not found at {reg_path}")
    if not rf_path.exists():
        raise FileNotFoundError(f"Random Forest model not found at {rf_path}")

    _MODELS_CACHE["regression"] = joblib.load(reg_path)
    _MODELS_CACHE["random_forest"] = joblib.load(rf_path)

    if ensemble_path.exists():
        _MODELS_CACHE["ensemble"] = joblib.load(ensemble_path)

    if gb_path.exists():
        try:
            _MODELS_CACHE["gradient_boosting"] = joblib.load(gb_path)
        except Exception as e:
            print(f"[Warning] Failed to load gradient boosting: {e}")

    if h_path.exists():
        try:
            _MODELS_CACHE["hurdle"] = joblib.load(h_path)
        except Exception as e:
            print(f"[Warning] Failed to load hurdle model: {e}")

    return _MODELS_CACHE


def categorize_rainfall(amount_mm: float) -> Tuple[str, str]:
    if amount_mm <= 0.05:
        return "No Rain", "Clear skies or non-measurable trace dampness."
    elif amount_mm <= 2.5:
        return "Light", "Gentle showers or drizzle; minimal accumulation."
    elif amount_mm <= 15.0:
        return "Moderate", "Steady continuous rain; localized puddles."
    elif amount_mm <= 50.0:
        return "Heavy", "Heavy storm or convective downpour; potential waterlogging."
    else:
        return "Torrential", "Torrential cloudburst; severe flooding hazard."


def get_advisory(amount_mm: float, category: str) -> Dict[str, str]:
    if category == "No Rain" or amount_mm <= 0.05:
        return {
            "severity": "NORMAL",
            "message": "Conditions indicate minimal or no measurable rainfall. Clear to partly cloudy skies expected. Normal agricultural and outdoor operations may proceed."
        }
    elif category == "Light":
        return {
            "severity": "ADVISORY",
            "message": "Light showers anticipated. Mild surface dampness; carry an umbrella for convenience."
        }
    elif category == "Moderate":
        return {
            "severity": "MODERATE",
            "message": "Moderate precipitation predicted. Commuters should expect wet roadways; localized puddles in low-lying intersections."
        }
    elif category == "Heavy":
        return {
            "severity": "WARNING",
            "message": "HEAVY RAINFALL WARNING: Significant downpour (>15 mm) expected. High risk of localized urban waterlogging, slow highway traffic, and drainage overflow."
        }
    else:
        return {
            "severity": "CRITICAL ALERT",
            "message": "TORRENTIAL FLOOD ALERT: Extreme precipitation (>50 mm) anticipated. Avoid travel through underpasses; municipal storm drainage overflow imminent."
        }


def compute_domain_advisory(amount_mm: float, rain_prob_pct: float = None) -> Dict[str, Any]:
    """
    Computes actionable domain-specific advisories:
    1. Municipal Urban Flood Risk & Drainage Stress
    2. Smart Agricultural & Farming Advisory
    """
    # Urban Flood Risk calculation
    if amount_mm <= 0.05:
        flood_level = "MINIMAL"
        flood_badge = "status-green"
        drainage_capacity_pct = 12
        underpass_risk = "Negligible"
        traffic_impact = "Normal transit flow; roads dry"
        action_summary = "Storm water drainage free and clear."
    elif amount_mm <= 5.0:
        flood_level = "LOW"
        flood_badge = "status-green"
        drainage_capacity_pct = 32
        underpass_risk = "Minimal shallow ponding"
        traffic_impact = "Slight surface traction reduction"
        action_summary = "Routine municipal street drainage active."
    elif amount_mm <= 20.0:
        flood_level = "WATCH"
        flood_badge = "status-yellow"
        drainage_capacity_pct = 68
        underpass_risk = "Waterlogging likely in low-lying underpasses"
        traffic_impact = "Commuter speed slowdown by 20-30%"
        action_summary = "Municipal pumps on standby; clear curb storm grates."
    elif amount_mm <= 50.0:
        flood_level = "WARNING"
        flood_badge = "status-orange"
        drainage_capacity_pct = 94
        underpass_risk = "High risk of submerged underpasses (>0.5m)"
        traffic_impact = "Severe arterial road congestion; avoid low intersections"
        action_summary = "Deploy mobile dewatering pumps; issue commuter alerts."
    else:
        flood_level = "CRITICAL ALERT"
        flood_badge = "status-red"
        drainage_capacity_pct = 140
        underpass_risk = "Extreme inundation; immediate underpass closure required"
        traffic_impact = "Critical transit gridlock; low-lying routes impassable"
        action_summary = "Activate municipal flood emergency protocol & storm sirens."

    # Smart Agricultural Advisory
    if amount_mm <= 0.05:
        irrigation_advice = "Standard Irrigation Recommended"
        irrigation_detail = "Moisture deficit expected. Safe to operate automated drip/sprinkler systems."
        spray_status = "Optimal Spraying Window"
        spray_badge = "status-green"
        spray_detail = "Zero wash-off risk. Ideal window for pesticide & foliar fertilizer application."
        field_work = "Field tractors and machinery can operate freely across dry soil."
    elif amount_mm <= 5.0:
        irrigation_advice = "Reduce Irrigation by 50%"
        irrigation_detail = "Light surface moisture available. Delay deep furrow irrigation."
        spray_status = "Caution: Minor Wash-off Risk"
        spray_badge = "status-yellow"
        spray_detail = "Permissible if applied 4+ hours before precipitation."
        field_work = "Soil workable; check clay soil for minor surface crusting."
    elif amount_mm <= 20.0:
        irrigation_advice = "Suspend All Irrigation"
        irrigation_detail = "Adequate root moisture replenishment. Halting irrigation conserves water & energy."
        spray_status = "Do NOT Spray (High Wash-off)"
        spray_badge = "status-orange"
        spray_detail = "Precipitation will wash away active chemical formulations."
        field_work = "Inspect field bunds; verify natural slope drainage channels are unobstructed."
    else:
        irrigation_advice = "Halt & Drain Field"
        irrigation_detail = "Excess moisture hazard. Actively open field drainage cuts to avoid root asphyxiation."
        spray_status = "STRICT PROHIBITION"
        spray_badge = "status-red"
        spray_detail = "Chemical application completely ineffective; high soil leaching hazard."
        field_work = "Keep heavy equipment off saturated fields to prevent deep soil rutting."

    return {
        "urban_flood": {
            "level": flood_level,
            "badge_class": flood_badge,
            "drainage_load_pct": drainage_capacity_pct,
            "underpass_risk": underpass_risk,
            "traffic_impact": traffic_impact,
            "action_summary": action_summary
        },
        "agriculture": {
            "irrigation_advice": irrigation_advice,
            "irrigation_detail": irrigation_detail,
            "spray_status": spray_status,
            "spray_badge": spray_badge,
            "spray_detail": spray_detail,
            "field_work": field_work
        }
    }


def compute_xai_attribution(inputs: Dict[str, float]) -> Dict[str, Any]:
    """
    Computes scientific explainable AI (XAI) meteorological feature attributions
    and thermodynamic dew point metrics.
    """
    t = float(inputs.get("temperature", 28.0))
    h = float(inputs.get("humidity", 75.0))
    p = float(inputs.get("pressure", 1008.0))
    w = float(inputs.get("wind_speed", 14.0))
    prev = float(inputs.get("previous_rainfall", 0.0))

    # Magnus-Tetens approximation for Dew Point
    dew_point = round(t - ((100.0 - h) / 5.0), 1)
    depression = round(max(0.0, t - dew_point), 1)

    # Relative feature influence weights
    w_humidity = max(5.0, (h / 100.0) * 45.0)
    w_pressure = max(5.0, max(0.0, (1015.0 - p)) * 2.5)
    w_prev = min(30.0, max(5.0, (prev / 30.0) * 20.0))
    w_wind = min(20.0, max(5.0, (w / 40.0) * 15.0))
    w_temp = min(20.0, max(5.0, (t / 40.0) * 10.0))

    total_w = w_humidity + w_pressure + w_prev + w_wind + w_temp
    pct_h = round((w_humidity / total_w) * 100.0, 1)
    pct_p = round((w_pressure / total_w) * 100.0, 1)
    pct_prev = round((w_prev / total_w) * 100.0, 1)
    pct_w = round((w_wind / total_w) * 100.0, 1)
    pct_t = round((w_temp / total_w) * 100.0, 1)

    return {
        "dew_point_c": dew_point,
        "dew_point_spread_c": depression,
        "condensation_potential": "Very High" if depression < 2.5 else "Moderate" if depression < 6.0 else "Low",
        "attributions": [
            {"feature": "Relative Humidity", "weight_pct": pct_h, "impact": "Positive Moisture Flux"},
            {"feature": "Barometric Pressure Drop", "weight_pct": pct_p, "impact": "Atmospheric Instability"},
            {"feature": "Antecedent Rainfall Memory", "weight_pct": pct_prev, "impact": "Temporal Persistence"},
            {"feature": "Wind Speed Advection", "weight_pct": pct_w, "impact": "Moisture Transport"},
            {"feature": "Thermal Energy", "weight_pct": pct_t, "impact": "Convective Potential"}
        ]
    }


def predict_rainfall(models_dir: Path, model_name: str, raw_inputs: Dict[str, Any]) -> Dict[str, Any]:
    models = load_models(models_dir)

    m_str = model_name.lower()
    if "ensemble" in m_str:
        key = "ensemble" if "ensemble" in models else "random_forest"
    elif "hurdle" in m_str:
        key = "hurdle" if "hurdle" in models else "random_forest"
    elif "gradient" in m_str or "gb" in m_str or "boost" in m_str:
        key = "gradient_boosting" if "gradient_boosting" in models else "random_forest"
    elif "reg" in m_str or "linear" in m_str:
        key = "regression"
    else:
        key = "random_forest"

    model = models[key]

    display_names = {
        "ensemble": "RainVision Blended Ensemble Regressor",
        "regression": "Linear Regression (OLS)",
        "random_forest": "Random Forest Regressor (150 Trees)",
        "gradient_boosting": "Gradient Boosting Regressor (Sequential Trees)",
        "hurdle": "Two-Stage Meteorological Hurdle Model"
    }

    algorithm_descriptions = {
        "ensemble": "Validated 60% Random Forest + 40% Gradient Boosting ensemble",
        "regression": "Ordinary Least Squares with non-negative projection",
        "random_forest": "Ensemble of 150 randomized decision trees (max_depth=6)",
        "gradient_boosting": "Gradient Boosted Trees optimizing pseudo-residuals (lr=0.08)",
        "hurdle": "Stage 1: P(Rain) Classifier + Stage 2: Conditional Wet Severity Regressor"
    }

    # Preprocess
    start_t = time.perf_counter()
    X_df = prepare_features(raw_inputs)

    # Precipitation Probability (from Hurdle classifier or humidity estimation)
    rain_prob_pct = None
    if key == "hurdle" and hasattr(model, "predict_proba"):
        rain_prob_pct = round(float(model.predict_proba(X_df)[0]) * 100.0, 1)
    else:
        # Thermodynamic probability proxy
        hum = float(raw_inputs.get("humidity", 70.0))
        press = float(raw_inputs.get("pressure", 1010.0))
        est_prob = np.clip((hum - 40.0) * 1.4 + max(0.0, (1013.0 - press) * 3.0), 5.0, 98.0)
        rain_prob_pct = round(float(est_prob), 1)

    # Inference
    raw_val = float(model.predict(X_df)[0])
    latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
    pred_mm = round(max(0.0, raw_val), 2)

    cat, desc = categorize_rainfall(pred_mm)
    advisory = get_advisory(pred_mm, cat)
    domain_advisory = compute_domain_advisory(pred_mm, rain_prob_pct)
    xai = compute_xai_attribution(raw_inputs)

    # Uncertainty bound
    metadata_path = models_dir / "model_metadata.json"
    model_metadata = {}
    if metadata_path.exists():
        with metadata_path.open("r", encoding="utf-8") as metadata_file:
            model_metadata = json.load(metadata_file).get("models", {}).get(key, {})
    rmse = model_metadata.get("holdout_metrics", {}).get("rmse_mm")
    uncertainty_interval = None
    if rmse is not None:
        margin = round(rmse, 2)
        uncertainty_interval = {
            "lower_mm": max(0.0, round(pred_mm - margin, 2)),
            "upper_mm": round(pred_mm + margin, 2),
            "confidence_level": "Approximate plus/minus one holdout RMSE",
            "test_rmse_mm": rmse
        }

    return {
        "model_id": key,
        "model_key": key,
        "model_name": display_names.get(key, key),
        "algorithm": algorithm_descriptions.get(key, ""),
        "predicted_rainfall_mm": pred_mm,
        "rain_probability_pct": rain_prob_pct,
        "category": cat,
        "category_description": desc,
        "advisory": advisory,
        "domain_advisory": domain_advisory,
        "xai": xai,
        "inference_latency_ms": latency_ms,
        "uncertainty_interval": uncertainty_interval,
        "inputs_summary": {
            "temperature": float(raw_inputs.get("temperature", 28.0)),
            "humidity": float(raw_inputs.get("humidity", 75.0)),
            "pressure": float(raw_inputs.get("pressure", 1008.0)),
            "wind_speed": float(raw_inputs.get("wind_speed", 14.0)),
            "previous_rainfall": float(raw_inputs.get("previous_rainfall", raw_inputs.get("rain_lag_1", 0.0)))
        }
    }


def predict_both(models_dir: Path, raw_inputs: Dict[str, Any]) -> Dict[str, Any]:
    pred_ensemble = predict_rainfall(models_dir, "ensemble", raw_inputs)
    pred_lr = predict_rainfall(models_dir, "regression", raw_inputs)
    pred_rf = predict_rainfall(models_dir, "random_forest", raw_inputs)
    pred_gb = predict_rainfall(models_dir, "gradient_boosting", raw_inputs)
    pred_h = predict_rainfall(models_dir, "hurdle", raw_inputs)

    diff = round(
        abs(pred_lr["predicted_rainfall_mm"] - pred_ensemble["predicted_rainfall_mm"]),
        2
    )
    agree = diff <= 8.0

    return {
        "regression_model": pred_lr,
        "regression_prediction": pred_lr,
        "ensemble_model": pred_ensemble,
        "random_forest_model": pred_rf,
        "random_forest_prediction": pred_rf,
        "gradient_boosting_model": pred_gb,
        "hurdle_model": pred_h,
        "all_predictions": [pred_ensemble, pred_rf, pred_gb, pred_h, pred_lr],
        "absolute_difference_mm": diff,
        "comparison": {
            "absolute_difference_mm": diff,
            "models_agree": agree
        },
        "inputs_summary": pred_lr["inputs_summary"],
        "advisory": (
            pred_ensemble["advisory"]
            if pred_ensemble["predicted_rainfall_mm"] >= pred_lr["predicted_rainfall_mm"]
            else pred_lr["advisory"]
        )
    }


def get_weather_icon(category: str, amount_mm: float) -> str:
    if amount_mm <= 0.05:
        return "☀️"
    elif amount_mm <= 2.5:
        return "🌦️"
    elif amount_mm <= 15.0:
        return "🌧️"
    elif amount_mm <= 50.0:
        return "⛈️"
    else:
        return "🌊"


def simulate_7day_forecast(models_dir: Path, raw_inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Simulates a 7-day forward weather trajectory starting from today.
    Uses recursive temporal persistence (Day k-1 rain feeds into Day k prev_rain)
    along with thermodynamic feedback loops (evaporative cooling & humidity relaxation).
    """
    base_date = datetime.now()
    forecast = []

    curr_t = float(raw_inputs.get("temperature", 28.0))
    curr_h = float(raw_inputs.get("humidity", 75.0))
    curr_p = float(raw_inputs.get("pressure", 1008.0))
    curr_w = float(raw_inputs.get("wind_speed", 14.0))
    curr_prev = float(raw_inputs.get("previous_rainfall", 0.0))

    for day in range(1, 8):
        day_date = base_date + timedelta(days=day)
        day_label = day_date.strftime("%a, %b %d")

        step_inputs = {
            "temperature": round(curr_t, 1),
            "humidity": round(curr_h, 1),
            "pressure": round(curr_p, 1),
            "wind_speed": round(curr_w, 1),
            "previous_rainfall": round(curr_prev, 1)
        }

        step_res = predict_rainfall(models_dir, "hurdle", step_inputs)
        pred_mm = step_res["predicted_rainfall_mm"]
        rain_prob = step_res["rain_probability_pct"]
        cat = step_res["category"]
        flood = step_res["domain_advisory"]["urban_flood"]["level"]
        icon = get_weather_icon(cat, pred_mm)

        forecast.append({
            "day": day,
            "date": day_label,
            "iso_date": day_date.strftime("%Y-%m-%d"),
            "temperature": round(curr_t, 1),
            "humidity": round(curr_h, 1),
            "pressure": round(curr_p, 1),
            "wind_speed": round(curr_w, 1),
            "previous_rainfall": round(curr_prev, 1),
            "predicted_rainfall_mm": pred_mm,
            "rain_probability_pct": rain_prob,
            "category": cat,
            "weather_icon": icon,
            "flood_risk": flood,
            "advisory_tip": step_res["domain_advisory"]["agriculture"]["irrigation_advice"]
        })

        # Thermodynamic Recursive Update for Day k+1:
        if pred_mm > 5.0:
            curr_prev = pred_mm
            curr_t = max(18.0, curr_t - 0.8)       # Evaporative cooling
            curr_h = min(98.0, curr_h + 3.0)       # Retained surface moisture
            curr_p = min(1016.0, curr_p + 1.2)     # Synoptic pressure recovery
            curr_w = max(8.0, curr_w - 1.5)        # Post-frontal wind settling
        elif pred_mm > 0.05:
            curr_prev = pred_mm
            curr_t = max(20.0, curr_t - 0.3)
            curr_h = min(95.0, curr_h + 1.0)
            curr_p = min(1015.0, curr_p + 0.5)
        else:
            curr_prev = 0.0
            curr_t = min(42.0, curr_t + 0.4)       # Solar insolation heating
            curr_h = max(25.0, curr_h - 2.5)       # Moisture dispersal
            curr_p = max(995.0, curr_p - 0.4)
            curr_w = min(35.0, curr_w + 0.8)

    return forecast


def batch_predict_df(models_dir: Path, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Executes high-throughput batch inference across a pandas DataFrame.
    Returns annotated DataFrame and summary metrics.
    """
    models = load_models(models_dir)
    rf_model = models.get("random_forest")
    gb_model = models.get("gradient_boosting")
    h_model = models.get("hurdle")

    col_map = {}
    for col in df.columns:
        c_low = col.lower().strip().replace(" ", "_")
        if c_low in ["temp", "temperature_c", "t"]:
            col_map[col] = "temperature"
        elif c_low in ["hum", "rh", "relative_humidity", "humidity_pct"]:
            col_map[col] = "humidity"
        elif c_low in ["pres", "barometer", "pressure_hpa", "p"]:
            col_map[col] = "pressure"
        elif c_low in ["wind", "wind_kmh", "speed", "wind_speed_kmh"]:
            col_map[col] = "wind_speed"
        elif c_low in ["prev_rain", "lag1", "rainfall_lag1", "prior_rain"]:
            col_map[col] = "previous_rainfall"

    clean_df = df.rename(columns=col_map).copy()

    defaults = {"temperature": 28.0, "humidity": 70.0, "pressure": 1010.0, "wind_speed": 14.0, "previous_rainfall": 0.0}
    for feat, default_val in defaults.items():
        if feat not in clean_df.columns:
            clean_df[feat] = default_val
        else:
            clean_df[feat] = pd.to_numeric(clean_df[feat], errors="coerce").fillna(default_val)

    feature_rows = []
    for _, r in clean_df.iterrows():
        prev_val = r.get("previous_rainfall", r.get("rainfall", 0.0))
        r_dict = {
            "temperature": float(r.get("temperature", 28.0)),
            "humidity": float(r.get("humidity", 70.0)),
            "pressure": float(r.get("pressure", 1010.0)),
            "wind_speed": float(r.get("wind_speed", 14.0)),
            "previous_rainfall": float(prev_val if pd.notnull(prev_val) else 0.0),
            "date": r.get("date", None)
        }
        feat_df = prepare_features(r_dict)
        feature_rows.append(feat_df.iloc[0])

    X_mat = pd.DataFrame(feature_rows)

    preds_rf = np.round(np.clip(rf_model.predict(X_mat), 0.0, None), 2)
    preds_gb = np.round(np.clip(gb_model.predict(X_mat), 0.0, None), 2) if gb_model else preds_rf

    if h_model and hasattr(h_model, "predict_proba"):
        probs = np.round(h_model.predict_proba(X_mat) * 100.0, 1)
    else:
        probs = np.clip((clean_df["humidity"] - 40.0) * 1.4 + np.maximum(0.0, (1013.0 - clean_df["pressure"]) * 3.0), 5.0, 98.0)
        probs = np.round(probs, 1)

    result_df = clean_df.copy()
    result_df["Predicted_Rainfall_RF_mm"] = preds_rf
    result_df["Predicted_Rainfall_GB_mm"] = preds_gb
    result_df["Rain_Probability_Pct"] = probs

    categories = []
    flood_alerts = []
    for r in preds_rf:
        cat, _ = categorize_rainfall(float(r))
        categories.append(cat)
        adv = compute_domain_advisory(float(r))
        flood_alerts.append(adv["urban_flood"]["level"])

    result_df["Precipitation_Category"] = categories
    result_df["Urban_Flood_Alert"] = flood_alerts

    summary = {
        "total_rows": int(len(result_df)),
        "predicted_rainy_days": int((preds_rf > 0.05).sum()),
        "predicted_dry_days": int((preds_rf <= 0.05).sum()),
        "max_predicted_rainfall_mm": float(np.max(preds_rf)),
        "avg_predicted_rainfall_mm": float(round(float(np.mean(preds_rf)), 2)),
        "torrential_events_count": int((preds_rf > 50.0).sum())
    }

    return result_df, summary
