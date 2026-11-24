
"""
RainVision Flask Web Application & Meteorological ML API
Serves HTML5/CSS3/Vanilla JS frontend and connects with genuine trained ML models.
"""

import os
import io
import json
import time
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file, Response

from ml.preprocessing import FEATURE_COLUMNS, VALIDATION_BOUNDS, validate_weather_inputs
from ml.prediction import (
    load_models, predict_rainfall, predict_both, categorize_rainfall,
    simulate_7day_forecast, batch_predict_df
)
from ml.evaluation import evaluate_models

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"
MASTER_EXCEL_PATH = DATA_DIR / "RainVision_Historical_1985_to_Today.xlsx"
TEST_DATA_PATH = DATA_DIR / "test.csv"
CLEAN_DATA_PATH = DATA_DIR / "rainfall_clean.csv"

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static")
)

# Global caches
_DATASET_CACHE = None
_HISTORY_CACHE = []
_LAST_BATCH_RESULT_CSV = None


def load_dataset() -> pd.DataFrame:
    global _DATASET_CACHE
    if _DATASET_CACHE is None:
        if MASTER_EXCEL_PATH.exists():
            _DATASET_CACHE = pd.read_excel(MASTER_EXCEL_PATH, sheet_name="Rainfall_Data_1985_to_Today")
        elif CLEAN_DATA_PATH.exists():
            _DATASET_CACHE = pd.read_csv(CLEAN_DATA_PATH)
        else:
            raise FileNotFoundError(f"Master dataset file not found at {MASTER_EXCEL_PATH} or {CLEAN_DATA_PATH}")
    return _DATASET_CACHE


# ---------------------------------------------------------------------
# Web Frontend Route
# ---------------------------------------------------------------------

@app.route("/")
@app.route("/dashboard")
@app.route("/prediction")
@app.route("/compare")
@app.route("/explorer")
@app.route("/analytics")
@app.route("/about")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------
# REST API Endpoints
# ---------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def api_health():
    """Return backend status and actual model availability."""
    reg_exists = (MODELS_DIR / "regression_model.joblib").exists()
    rf_exists = (MODELS_DIR / "random_forest_model.joblib").exists()
    gb_exists = (MODELS_DIR / "gradient_boosting_model.joblib").exists()
    h_exists = (MODELS_DIR / "hurdle_model.joblib").exists()
    ensemble_exists = (MODELS_DIR / "ensemble_model.joblib").exists()
    data_exists = MASTER_EXCEL_PATH.exists() or CLEAN_DATA_PATH.exists()

    return jsonify({
        "status": "online" if (reg_exists and rf_exists and data_exists) else "degraded",
        "platform": "RainVision Meteorological ML & Climate Analytics System",
        "version": "2.2.0",
        "models_available": {
            "regression_model": reg_exists,
            "random_forest_model": rf_exists,
            "gradient_boosting_model": gb_exists,
            "hurdle_model": h_exists,
            "ensemble_model": ensemble_exists
        },
        "models_count": sum([reg_exists, rf_exists, gb_exists, h_exists, ensemble_exists]),
        "dataset_loaded": data_exists,
        "input_features_count": len(FEATURE_COLUMNS),
        "target_variable": "rainfall (continuous millimeters, mm)",
        "timestamp": datetime.now().isoformat()
    })


@app.route("/api/dashboard/summary", methods=["GET"])
def api_dashboard_summary():
    """Return dataset statistics calculated from real project data."""
    try:
        df = load_dataset()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    total_records = int(len(df))
    total_rain = float(df["rainfall"].sum())
    avg_rain = float(df["rainfall"].mean())
    max_rain = float(df["rainfall"].max())
    min_rain = float(df["rainfall"].min())

    rainy_days = int((df["rainfall"] > 0.05).sum())
    dry_days = total_records - rainy_days
    rainy_pct = round((rainy_days / total_records) * 100, 1)

    date_min = str(df["date"].min()) if "date" in df.columns else "N/A"
    date_max = str(df["date"].max()) if "date" in df.columns else "N/A"

    # Monthly averages
    df["month"] = pd.to_datetime(df["date"]).dt.month
    monthly_agg = df.groupby("month")["rainfall"].agg(["sum", "mean"]).reset_index()
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly_data = []
    for _, row in monthly_agg.iterrows():
        m_idx = int(row["month"]) - 1
        monthly_data.append({
            "month": month_names[m_idx] if 0 <= m_idx < 12 else str(row["month"]),
            "total_mm": round(float(row["sum"]), 1),
            "average_mm": round(float(row["mean"]), 2),
            "is_monsoon": m_idx in [5, 6, 7, 8]
        })

    # Yearly totals
    df["year"] = pd.to_datetime(df["date"]).dt.year
    yearly_agg = df.groupby("year")["rainfall"].agg(["sum", "mean", "count"]).reset_index()
    yearly_data = []
    for _, row in yearly_agg.iterrows():
        yearly_data.append({
            "year": str(int(row["year"])),
            "total_mm": round(float(row["sum"]), 1),
            "average_mm": round(float(row["mean"]), 2),
            "days_count": int(row["count"])
        })

    # Rainfall frequency distribution bins
    b_dry = int((df["rainfall"] <= 0.05).sum())
    b_light = int(((df["rainfall"] > 0.05) & (df["rainfall"] <= 2.5)).sum())
    b_mod = int(((df["rainfall"] > 2.5) & (df["rainfall"] <= 15.0)).sum())
    b_heavy = int(((df["rainfall"] > 15.0) & (df["rainfall"] <= 50.0)).sum())
    b_torrential = int((df["rainfall"] > 50.0).sum())

    distribution_bins = [
        {"range": "0 mm (Dry)", "count": b_dry, "label": "Dry / Trace"},
        {"range": "0.1–2.5 mm", "count": b_light, "label": "Light"},
        {"range": "2.6–15 mm", "count": b_mod, "label": "Moderate"},
        {"range": "15.1–50 mm", "count": b_heavy, "label": "Heavy"},
        {"range": "> 50 mm", "count": b_torrential, "label": "Torrential"}
    ]

    # Recent 30 days trends
    recent_records = df.tail(30)[["date", "temperature", "humidity", "pressure", "wind_speed", "rainfall"]].to_dict(orient="records")

    latest_pred = _HISTORY_CACHE[0] if _HISTORY_CACHE else None

    return jsonify({
        "kpis": {
            "total_records": total_records,
            "total_historical_rainfall_mm": round(total_rain, 1),
            "average_historical_rainfall_mm": round(avg_rain, 2),
            "max_recorded_rainfall_mm": round(max_rain, 1),
            "min_recorded_rainfall_mm": round(min_rain, 1),
            "rainy_days_count": rainy_days,
            "dry_days_count": dry_days,
            "rainy_days_percentage": rainy_pct,
            "date_range": f"{date_min} to {date_max}",
            "location": "Metropolis Central Station",
            "models_count": sum(
                (MODELS_DIR / artifact).exists()
                for artifact in (
                    "regression_model.joblib",
                    "random_forest_model.joblib",
                    "gradient_boosting_model.joblib",
                    "hurdle_model.joblib",
                    "ensemble_model.joblib",
                )
            ),
            "latest_prediction": latest_pred
        },
        "monthly_distribution": monthly_data,
        "yearly_comparison": yearly_data,
        "rainfall_distribution": distribution_bins,
        "recent_trends": recent_records
    })


@app.route("/api/dataset/columns", methods=["GET"])
def api_dataset_columns():
    """Return available column names and data types."""
    try:
        df = load_dataset()
        cols = []
        for col in df.columns:
            dtype_str = str(df[col].dtype)
            missing = int(df[col].isnull().sum())
            cols.append({
                "name": col,
                "data_type": dtype_str,
                "missing_count": missing,
                "missing_pct": round((missing / len(df)) * 100, 1),
                "is_feature": col in FEATURE_COLUMNS,
                "is_target": col == "rainfall"
            })
        return jsonify({
            "total_columns": len(cols),
            "total_rows": len(df),
            "columns": cols
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dataset/preview", methods=["GET"])
def api_dataset_preview():
    """Return a paginated dataset preview with search and sorting."""
    try:
        df = load_dataset().copy()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Search filter
    search_query = request.args.get("search", "").strip().lower()
    if search_query:
        mask = df["date"].astype(str).str.lower().str.contains(search_query) | \
               df["location"].astype(str).str.lower().str.contains(search_query)
        df = df[mask]

    # Year filter
    year_filter = request.args.get("year", "").strip()
    if year_filter and year_filter != "all":
        df = df[df["date"].astype(str).str.startswith(year_filter)]

    # Rainfall filter
    rain_filter = request.args.get("rain", "all").strip()
    if rain_filter == "rain-only":
        df = df[df["rainfall"] > 0.05]
    elif rain_filter == "dry-only":
        df = df[df["rainfall"] <= 0.05]
    elif rain_filter == "heavy-only":
        df = df[df["rainfall"] > 15.0]

    # Sorting
    sort_by = request.args.get("sort_by", "date")
    sort_order = request.args.get("sort_order", "desc")
    if sort_by in df.columns:
        df = df.sort_values(by=sort_by, ascending=(sort_order == "asc"))

    total_records = len(df)
    page = max(1, int(request.args.get("page", 1)))
    limit = max(5, min(100, int(request.args.get("limit", 20))))
    total_pages = max(1, int(np.ceil(total_records / limit)))
    start_idx = (page - 1) * limit
    page_df = df.iloc[start_idx : start_idx + limit]

    # Convert to json-friendly records
    records = []
    for _, r in page_df.iterrows():
        cat, _ = categorize_rainfall(float(r["rainfall"]))
        records.append({
            "date": str(r["date"]),
            "location": str(r.get("location", "Metropolis Central")),
            "rainfall": round(float(r["rainfall"]), 2),
            "category": cat,
            "temperature": round(float(r["temperature"]), 1),
            "humidity": round(float(r["humidity"]), 1),
            "pressure": round(float(r["pressure"]), 1),
            "wind_speed": round(float(r["wind_speed"]), 1),
            "previous_rainfall": round(float(r.get("previous_rainfall", 0.0)), 2)
        })

    return jsonify({
        "records": records,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "total_records": total_records
        }
    })


@app.route("/api/models", methods=["GET"])
def api_models():
    """Return discovered model names, availability, and input schema."""
    reg_exists = (MODELS_DIR / "regression_model.joblib").exists()
    rf_exists = (MODELS_DIR / "random_forest_model.joblib").exists()
    gb_exists = (MODELS_DIR / "gradient_boosting_model.joblib").exists()
    h_exists = (MODELS_DIR / "hurdle_model.joblib").exists()
    ensemble_exists = (MODELS_DIR / "ensemble_model.joblib").exists()

    try:
        eval_path = MASTER_EXCEL_PATH if MASTER_EXCEL_PATH.exists() else TEST_DATA_PATH
        metrics = evaluate_models(MODELS_DIR, eval_path)["models"]
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    model_definitions = [
        {
            "id": "ensemble",
            "name": "RainVision Blended Ensemble",
            "full_name": "RainVision Blended Ensemble Regressor",
            "algorithm": "Random Forest (60%) + Gradient Boosting (40%)",
            "is_available": ensemble_exists,
            "file": "ensemble_model.joblib",
            "description": "Validated blended model combining the project’s Random Forest and Gradient Boosting regressors."
        },
        {
            "id": "random_forest",
            "name": "Random Forest Regressor",
            "full_name": "Random Forest Regressor (150 Trees)",
            "algorithm": "Ensemble of randomized decision trees",
            "is_available": rf_exists,
            "file": "random_forest_model.joblib",
            "description": "Non-linear ensemble capturing atmospheric variable interactions."
        },
        {
            "id": "gradient_boosting",
            "name": "Gradient Boosting Regressor",
            "full_name": "Gradient Boosting Regressor (Sequential Trees)",
            "algorithm": "Gradient-boosted decision trees",
            "is_available": gb_exists,
            "file": "gradient_boosting_model.joblib",
            "description": "Sequential boosting model for rainfall amount prediction."
        },
        {
            "id": "hurdle",
            "name": "Two-Stage Hurdle Model",
            "full_name": "Two-Stage Hurdle Precipitation Model",
            "algorithm": "Rain occurrence classification followed by wet-day severity regression",
            "is_available": h_exists,
            "file": "hurdle_model.joblib",
            "description": "Two-stage rainfall occurrence and amount model."
        },
        {
            "id": "regression",
            "name": "Linear Regression (OLS)",
            "full_name": "Linear Regression (Ordinary Least Squares)",
            "algorithm": "Ordinary least squares with non-negative output projection",
            "is_available": reg_exists,
            "file": "regression_model.joblib",
            "description": "Parametric linear baseline for rainfall amount prediction."
        }
    ]
    for model in model_definitions:
        measured = metrics.get(model["id"], {})
        model.update({
            "target": "rainfall (continuous millimeters, mm)",
            "features_count": len(FEATURE_COLUMNS),
            "r2_score": measured.get("r2_score"),
            "mae_mm": measured.get("mae_mm"),
            "rmse_mm": measured.get("rmse_mm"),
            "training_time": (
                f"{measured['training_time_s']:.3f}s"
                if measured.get("training_time_s") is not None else None
            )
        })

    return jsonify({
        "models": model_definitions,
        "input_features": [
            {"name": "temperature", "label": "Ambient Temperature", "unit": "°C", "min": -10, "max": 60, "default": 28.0},
            {"name": "humidity", "label": "Relative Humidity", "unit": "%", "min": 0, "max": 100, "default": 85.0},
            {"name": "pressure", "label": "Barometric Pressure", "unit": "hPa", "min": 850, "max": 1100, "default": 1004.0},
            {"name": "wind_speed", "label": "Wind Speed", "unit": "km/h", "min": 0, "max": 180, "default": 16.0},
            {"name": "previous_rainfall", "label": "Previous Day Rainfall", "unit": "mm", "min": 0, "max": 500, "default": 15.0}
        ]
    })


@app.route("/api/models/metrics", methods=["GET"])
def api_models_metrics():
    """Return model metrics measured on the workbook's held-out test period."""
    try:
        eval_path = MASTER_EXCEL_PATH if MASTER_EXCEL_PATH.exists() else TEST_DATA_PATH
        results = evaluate_models(MODELS_DIR, eval_path)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/predict", methods=["POST"])
def api_predict():
    """Execute the selected model and return its actual prediction."""
    payload = request.get_json(force=True, silent=True) or {}
    model_name = payload.get("model", "ensemble")

    try:
        result = predict_rainfall(MODELS_DIR, model_name, payload)

        # Save to persistent history log
        history_entry = {
            "id": f"PRED-{int(time.time() * 1000)}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model": result["model_name"],
            "predicted_rainfall_mm": result["predicted_rainfall_mm"],
            "category": result["category"],
            "temperature": result["inputs_summary"]["temperature"],
            "humidity": result["inputs_summary"]["humidity"],
            "pressure": result["inputs_summary"]["pressure"],
            "wind_speed": result["inputs_summary"]["wind_speed"],
            "previous_rainfall": result["inputs_summary"]["previous_rainfall"]
        }
        _HISTORY_CACHE.insert(0, history_entry)
        if len(_HISTORY_CACHE) > 200:
            _HISTORY_CACHE.pop()

        result["prediction_id"] = history_entry["id"]
        result["timestamp"] = history_entry["timestamp"]
        return jsonify(result)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Inference execution failed: {str(e)}"}), 500


@app.route("/api/predict/compare", methods=["POST"])
def api_predict_compare():
    """Run both compatible models against the same input and return their predictions."""
    payload = request.get_json(force=True, silent=True) or {}

    try:
        comparison = predict_both(MODELS_DIR, payload)
        return jsonify(comparison)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Model comparison failed: {str(e)}"}), 500


@app.route("/api/predict/7day-forecast", methods=["POST"])
def api_predict_7day_forecast():
    """Simulate a rolling 7-day meteorological forecast trajectory."""
    payload = request.get_json(force=True, silent=True) or {}
    try:
        forecast = simulate_7day_forecast(MODELS_DIR, payload)
        return jsonify({
            "success": True,
            "forecast_days": len(forecast),
            "forecast": forecast
        })
    except Exception as e:
        return jsonify({"error": f"Failed to simulate 7-day forecast: {str(e)}"}), 500


@app.route("/api/rainfall/trends", methods=["GET"])
def api_rainfall_trends():
    """Return historical rainfall trends and seasonality."""
    try:
        df = load_dataset()
        df["month"] = pd.to_datetime(df["date"]).dt.month
        monthly_avg = df.groupby("month")["rainfall"].mean().to_dict()
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        monthly_series = [round(float(monthly_avg.get(i, 0.0)), 2) for i in range(1, 13)]

        # Annual trend
        df["year"] = pd.to_datetime(df["date"]).dt.year
        yearly_avg = df.groupby("year")["rainfall"].sum().to_dict()
        years = sorted(list(yearly_avg.keys()))
        yearly_series = [round(float(yearly_avg[y]), 1) for y in years]

        return jsonify({
            "months": month_names,
            "monthly_means": monthly_series,
            "years": [str(y) for y in years],
            "yearly_totals": yearly_series,
            "station": "Metropolis Central Station"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/predictions/history", methods=["GET"])
def api_predictions_history():
    """Return in-memory audit history of predictions."""
    return jsonify({
        "total": len(_HISTORY_CACHE),
        "history": _HISTORY_CACHE
    })


@app.route("/api/reports/export", methods=["GET"])
def api_reports_export():
    """Download prediction results, metrics, or dataset as CSV."""
    report_type = request.args.get("type", "predictions")

    if report_type == "predictions":
        if not _HISTORY_CACHE:
            csv_content = "id,timestamp,model,predicted_rainfall_mm,category,temperature,humidity,pressure,wind_speed,previous_rainfall\n"
        else:
            df_hist = pd.DataFrame(_HISTORY_CACHE)
            csv_content = df_hist.to_csv(index=False)
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=rainvision_predictions.csv"}
        )

    elif report_type == "metrics":
        try:
            eval_path = MASTER_EXCEL_PATH if MASTER_EXCEL_PATH.exists() else TEST_DATA_PATH
            metrics = evaluate_models(MODELS_DIR, eval_path)
            rows = []
            for k, v in metrics["models"].items():
                rows.append({
                    "model": v["name"],
                    "algorithm": v["algorithm"],
                    "r2_score": v["r2_score"],
                    "mae_mm": v["mae_mm"],
                    "rmse_mm": v["rmse_mm"],
                    "mse_mm2": v["mse_mm2"],
                    "training_time_s": v["training_time_s"],
                    "inference_time_ms": v["inference_time_ms"]
                })
            df_m = pd.DataFrame(rows)
            return Response(
                df_m.to_csv(index=False),
                mimetype="text/csv",
                headers={"Content-Disposition": "attachment;filename=rainvision_model_metrics.csv"}
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif report_type == "dataset":
        try:
            df = load_dataset()
            return Response(
                df.to_csv(index=False),
                mimetype="text/csv",
                headers={"Content-Disposition": "attachment;filename=rainvision_dataset.csv"}
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif report_type in ["excel", "xlsx"]:
        excel_path = DATA_DIR / "RainVision_Historical_1985_to_Today.xlsx"
        if excel_path.exists():
            return send_file(
                excel_path,
                as_attachment=True,
                download_name="RainVision_Historical_1985_to_Today.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        return jsonify({"error": "Excel file not found on server."}), 404

    elif report_type == "pdf":
        pdf_path = BASE_DIR.parent / "RainVision_Recent_Changes_Report.pdf"
        if pdf_path.exists():
            return send_file(
                pdf_path,
                as_attachment=False,
                download_name="RainVision_Recent_Changes_Report.pdf",
                mimetype="application/pdf"
            )
        return jsonify({"error": "Report PDF not found on server."}), 404

    return jsonify({"error": "Invalid export type. Supported: 'predictions', 'metrics', 'dataset', 'excel', 'pdf'."}), 400


@app.route("/api/download-report-pdf", methods=["GET"])
def api_download_report_pdf():
    """View or download the executive PDF report in browser."""
    pdf_path = BASE_DIR.parent / "RainVision_Recent_Changes_Report.pdf"
    if pdf_path.exists():
        return send_file(
            pdf_path,
            as_attachment=False,
            download_name="RainVision_Recent_Changes_Report.pdf",
            mimetype="application/pdf"
        )
    return jsonify({"error": "Report PDF not found on server."}), 404


@app.route("/api/dataset/download-excel", methods=["GET"])
def api_download_excel():
    """Download the complete multi-sheet Excel workbook from 1985 to today."""
    excel_path = DATA_DIR / "RainVision_Historical_1985_to_Today.xlsx"
    if excel_path.exists():
        return send_file(
            excel_path,
            as_attachment=True,
            download_name="RainVision_Historical_1985_to_Today.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    return jsonify({"error": "Excel file not found on server."}), 404


@app.route("/api/weather/live", methods=["GET"])
def api_weather_live():
    """
    Fetch live real-time weather parameters for popular cities or coordinates.
    Tries Open-Meteo public API with fast fallback to calibrated climatological profile.
    """
    import urllib.request

    CITY_COORDINATES = {
        "ahmedabad": {"name": "Ahmedabad, India", "lat": 23.0225, "lon": 72.5714, "temp": 28.5, "hum": 62.0, "pres": 1012.0, "wind": 11.0, "prev": 0.0},
        "mumbai": {"name": "Mumbai, India", "lat": 19.0760, "lon": 72.8777, "temp": 29.0, "hum": 78.0, "pres": 1010.0, "wind": 14.5, "prev": 0.2},
        "delhi": {"name": "Delhi (NCR), India", "lat": 28.6139, "lon": 77.2090, "temp": 25.0, "hum": 54.0, "pres": 1014.0, "wind": 9.0, "prev": 0.0},
        "bengaluru": {"name": "Bengaluru, India", "lat": 12.9716, "lon": 77.5946, "temp": 24.5, "hum": 72.0, "pres": 1013.0, "wind": 13.0, "prev": 1.5},
        "kolkata": {"name": "Kolkata, India", "lat": 22.5726, "lon": 88.3639, "temp": 27.5, "hum": 75.0, "pres": 1011.0, "wind": 10.5, "prev": 0.0},
        "chennai": {"name": "Chennai, India", "lat": 13.0827, "lon": 80.2707, "temp": 29.5, "hum": 82.0, "pres": 1009.0, "wind": 16.0, "prev": 4.2},
        "london": {"name": "London, United Kingdom", "lat": 51.5074, "lon": -0.1278, "temp": 14.0, "hum": 84.0, "pres": 1015.0, "wind": 18.0, "prev": 2.1},
        "new_york": {"name": "New York, USA", "lat": 40.7128, "lon": -74.0060, "temp": 15.5, "hum": 68.0, "pres": 1018.0, "wind": 15.0, "prev": 0.0},
        "tokyo": {"name": "Tokyo, Japan", "lat": 35.6762, "lon": 139.6503, "temp": 18.0, "hum": 70.0, "pres": 1016.0, "wind": 12.0, "prev": 0.0}
    }

    city_key = request.args.get("city", "ahmedabad").lower().replace(" ", "_")
    profile = CITY_COORDINATES.get(city_key, CITY_COORDINATES["ahmedabad"])

    lat = float(request.args.get("lat", profile["lat"]))
    lon = float(request.args.get("lon", profile["lon"]))
    city_name = request.args.get("name", profile["name"])

    # Attempt live query from Open-Meteo (zero API keys required)
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,precipitation"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "RainVision/2.0"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode())
            current = data.get("current", {})
            return jsonify({
                "city": city_name,
                "latitude": lat,
                "longitude": lon,
                "temperature": round(float(current.get("temperature_2m", profile["temp"])), 1),
                "humidity": round(float(current.get("relative_humidity_2m", profile["hum"])), 1),
                "pressure": round(float(current.get("surface_pressure", profile["pres"])), 1),
                "wind_speed": round(float(current.get("wind_speed_10m", profile["wind"])), 1),
                "previous_rainfall": round(float(current.get("precipitation", profile["prev"])), 1),
                "source": "Open-Meteo Real-Time Weather Satellite API",
                "is_live_satellite": True,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
    except Exception:
        # Seamless fallback with realistic station profile
        return jsonify({
            "city": city_name,
            "latitude": lat,
            "longitude": lon,
            "temperature": profile["temp"],
            "humidity": profile["hum"],
            "pressure": profile["pres"],
            "wind_speed": profile["wind"],
            "previous_rainfall": profile["prev"],
            "source": "Calibrated Station Climatological Profile",
            "is_live_satellite": False,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })


@app.route("/api/dataset/upload", methods=["POST"])
def api_dataset_upload():
    """
    Accept user uploaded CSV, validate schema, and execute batch ML inference.
    Stores the annotated result for download and returns preview records.
    """
    global _LAST_BATCH_RESULT_CSV
    if "file" not in request.files:
        return jsonify({"error": "No CSV file provided in upload form."}), 400

    file = request.files["file"]
    if not file.filename.endswith(".csv"):
        return jsonify({"error": "Uploaded file must have a .csv extension."}), 400

    try:
        content = file.read().decode("utf-8", errors="replace")
        csv_io = io.StringIO(content)
        uploaded_df = pd.read_csv(csv_io)

        rows = len(uploaded_df)
        cols = len(uploaded_df.columns)
        missing_count = int(uploaded_df.isnull().sum().sum())
        duplicates = int(uploaded_df.duplicated().sum())

        # Cap batch processing at 1,000 rows for real-time safety
        batch_slice = uploaded_df.head(1000).copy()
        annotated_df, summary = batch_predict_df(MODELS_DIR, batch_slice)

        # Store annotated CSV in memory for user download
        out_buf = io.StringIO()
        annotated_df.to_csv(out_buf, index=False)
        _LAST_BATCH_RESULT_CSV = out_buf.getvalue()

        # Generate preview records (first 5)
        preview_records = []
        for _, r in annotated_df.head(5).iterrows():
            preview_records.append({
                "temperature": round(float(r.get("temperature", 28.0)), 1),
                "humidity": round(float(r.get("humidity", 70.0)), 1),
                "pressure": round(float(r.get("pressure", 1010.0)), 1),
                "predicted_rf": round(float(r.get("Predicted_Rainfall_RF_mm", 0.0)), 2),
                "rain_prob": round(float(r.get("Rain_Probability_Pct", 0.0)), 1),
                "category": str(r.get("Precipitation_Category", "Dry")),
                "flood_alert": str(r.get("Urban_Flood_Alert", "MINIMAL"))
            })

        return jsonify({
            "success": True,
            "filename": file.filename,
            "rows": rows,
            "columns": list(uploaded_df.columns),
            "missing_values": missing_count,
            "duplicate_rows": duplicates,
            "batch_summary": summary,
            "preview_records": preview_records,
            "download_url": "/api/dataset/download-batch-result",
            "message": f"Successfully parsed and executed ML inference on {min(rows, 1000)} rows from '{file.filename}'."
        })
    except Exception as e:
        return jsonify({"error": f"Failed to process CSV file: {str(e)}"}), 400


@app.route("/api/dataset/download-batch-result", methods=["GET"])
def api_download_batch_result():
    """Download the annotated batch prediction results as CSV."""
    global _LAST_BATCH_RESULT_CSV
    if _LAST_BATCH_RESULT_CSV:
        return Response(
            _LAST_BATCH_RESULT_CSV,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=RainVision_Batch_Predictions.csv"}
        )
    return jsonify({"error": "No batch prediction results available to download."}), 404


# ---------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[RainVision] Flask Web Application starting on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
