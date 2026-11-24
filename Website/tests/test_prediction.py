"""
Automated Integration and Unit Test Suite for RainVision Web Application
Tests ML inference, preprocessing boundaries, API endpoints, and real data integration.
Uses Python's standard unittest framework.
"""

import io
import json
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app
from ml.preprocessing import VALIDATION_BOUNDS, validate_weather_inputs, prepare_features
from ml.prediction import load_models, predict_rainfall, predict_both, categorize_rainfall
from ml.evaluation import evaluate_models


class RainVisionTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_01_api_health(self):
        """Verify backend health endpoint reports operational status and loaded models."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "online")
        self.assertTrue(data["models_available"]["regression_model"])
        self.assertTrue(data["models_available"]["random_forest_model"])
        self.assertTrue(data["dataset_loaded"])
        self.assertEqual(data["input_features_count"], 17)

    def test_02_dashboard_summary(self):
        """Verify KPI metrics and distribution charts are computed from the real dataset."""
        response = self.client.get("/api/dashboard/summary")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        kpis = data["kpis"]
        self.assertGreaterEqual(kpis["total_records"], 15000)
        self.assertEqual(kpis["models_count"], 5)
        self.assertGreater(kpis["average_historical_rainfall_mm"], 0)
        self.assertGreater(kpis["max_recorded_rainfall_mm"], 50)
        self.assertEqual(len(data["monthly_distribution"]), 12)
        self.assertGreaterEqual(len(data["yearly_comparison"]), 9)
        self.assertEqual(len(data["rainfall_distribution"]), 5)

    def test_03_models_metadata(self):
        """Verify models endpoint returns regression, random forest, and advanced schemas."""
        response = self.client.get("/api/models")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertGreaterEqual(len(data["models"]), 2)
        model_ids = [m["id"] for m in data["models"]]
        self.assertIn("regression", model_ids)
        self.assertIn("random_forest", model_ids)
        self.assertIn("ensemble", model_ids)
        self.assertTrue(all(m["is_available"] for m in data["models"]))
        self.assertTrue(all(m["r2_score"] is not None for m in data["models"]))

    def test_04_models_metrics(self):
        """Verify evaluation metrics on test.csv."""
        response = self.client.get("/api/models/metrics")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("models", data)
        self.assertEqual(data["test_records_count"], 546)
        self.assertIn("random_forest", data["models"])
        self.assertIn("regression", data["models"])
        self.assertTrue(data["sample_predictions"])
        self.assertEqual(
            set(data["sample_predictions"][0]),
            {"actual_mm", "ensemble_predicted_mm", "rf_predicted_mm", "reg_predicted_mm"}
        )

        rf = data["models"]["random_forest"]
        reg = data["models"]["regression"]
        ensemble = data["models"]["ensemble"]
        self.assertGreaterEqual(rf["mae_mm"], 0.0)
        self.assertGreaterEqual(reg["mae_mm"], 0.0)
        self.assertGreater(ensemble["r2_score"], rf["r2_score"])

    def test_05a_predict_validated_ensemble(self):
        """Verify the validated blended ensemble is available to the website."""
        response = self.client.post("/api/predict", json={
            "model": "ensemble",
            "temperature": 29.0,
            "humidity": 82.0,
            "pressure": 1002.0,
            "wind_speed": 18.0,
            "previous_rainfall": 10.0
        })
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertEqual(result["model_id"], "ensemble")
        self.assertGreaterEqual(result["predicted_rainfall_mm"], 0.0)
        self.assertIsNotNone(result["uncertainty_interval"])

    def test_05_predict_random_forest_valid(self):
        """Verify inference for Random Forest model on valid weather inputs."""
        payload = {
            "model": "random_forest",
            "temperature": 28.0,
            "humidity": 85.0,
            "pressure": 1004.0,
            "wind_speed": 16.5,
            "previous_rainfall": 15.0
        }
        response = self.client.post("/api/predict", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["model_id"], "random_forest")
        self.assertIn("predicted_rainfall_mm", data)
        self.assertGreaterEqual(data["predicted_rainfall_mm"], 0.0)
        self.assertIn("category", data)
        self.assertIn("advisory", data)
        self.assertIn("xai", data)
        self.assertIn("dew_point_c", data["xai"])

    def test_05b_predict_gradient_boosting(self):
        """Verify inference for Gradient Boosting model."""
        payload = {
            "model": "gradient_boosting",
            "temperature": 29.0,
            "humidity": 82.0,
            "pressure": 1002.0,
            "wind_speed": 18.0,
            "previous_rainfall": 10.0
        }
        response = self.client.post("/api/predict", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["model_id"], "gradient_boosting")
        self.assertGreaterEqual(data["predicted_rainfall_mm"], 0.0)

    def test_05c_predict_hurdle_model(self):
        """Verify inference for Two-Stage Hurdle model with Rain Probability."""
        payload = {
            "model": "hurdle",
            "temperature": 30.0,
            "humidity": 90.0,
            "pressure": 999.0,
            "wind_speed": 22.0,
            "previous_rainfall": 25.0
        }
        response = self.client.post("/api/predict", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["model_id"], "hurdle")
        self.assertIn("rain_probability_pct", data)
        self.assertGreaterEqual(data["rain_probability_pct"], 0.0)

    def test_06_predict_regression_valid(self):
        """Verify inference for Linear Regression model on valid weather inputs."""
        payload = {
            "model": "regression",
            "temperature": 32.0,
            "humidity": 90.0,
            "pressure": 998.0,
            "wind_speed": 25.0,
            "previous_rainfall": 40.0
        }
        response = self.client.post("/api/predict", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["model_id"], "regression")
        self.assertGreaterEqual(data["predicted_rainfall_mm"], 0.0)

    def test_07_predict_validation_bounds(self):
        """Verify validation boundaries reject out-of-range atmospheric inputs."""
        invalid_payload = {
            "model": "random_forest",
            "temperature": 99.0,  # Max is 60°C
            "humidity": 150.0,   # Max is 100%
            "pressure": 600.0,   # Min is 850 hPa
            "wind_speed": -5.0,  # Min is 0
            "previous_rainfall": -1.0
        }
        response = self.client.post("/api/predict", data=json.dumps(invalid_payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    def test_08_predict_compare(self):
        """Verify comparative inference returns predictions for both models and difference."""
        payload = {
            "temperature": 29.0,
            "humidity": 88.0,
            "pressure": 1002.0,
            "wind_speed": 18.0,
            "previous_rainfall": 20.0
        }
        response = self.client.post("/api/predict/compare", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("regression_model", data)
        self.assertIn("random_forest_model", data)
        self.assertIn("comparison", data)
        self.assertIn("absolute_difference_mm", data["comparison"])

    def test_09_dataset_preview(self):
        """Verify paginated dataset preview endpoint."""
        response = self.client.get("/api/dataset/preview?page=1&limit=10")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data["records"]), 10)
        self.assertEqual(data["pagination"]["page"], 1)
        self.assertEqual(data["pagination"]["limit"], 10)
        self.assertGreaterEqual(data["pagination"]["total_records"], 15000)

    def test_10_reports_export(self):
        """Verify report export endpoints deliver valid CSV headers and rows."""
        res_pred = self.client.get("/api/reports/export?type=predictions")
        self.assertEqual(res_pred.status_code, 200)
        self.assertIn("text/csv", res_pred.content_type)

        res_metrics = self.client.get("/api/reports/export?type=metrics")
        self.assertEqual(res_metrics.status_code, 200)
        self.assertIn("text/csv", res_metrics.content_type)

        res_dataset = self.client.get("/api/reports/export?type=dataset")
        self.assertEqual(res_dataset.status_code, 200)
        self.assertIn("text/csv", res_dataset.content_type)

    def test_11_csv_upload_validation(self):
        """Verify custom CSV upload validation without code execution."""
        sample_csv = "date,temperature,humidity,pressure,wind_speed,rainfall\n2024-01-01,25.0,70.0,1012.0,12.0,5.2\n"
        data = {
            "file": (io.BytesIO(sample_csv.encode("utf-8")), "custom_weather.csv")
        }
        response = self.client.post("/api/dataset/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 200)
        res_data = response.get_json()
        self.assertTrue(res_data["success"])
        self.assertEqual(res_data["rows"], 1)
        self.assertEqual(res_data["columns"], ["date", "temperature", "humidity", "pressure", "wind_speed", "rainfall"])

    def test_12_download_excel_file(self):
        """Verify downloading the master Excel workbook (.xlsx) from 1985 to today."""
        res_excel = self.client.get("/api/dataset/download-excel")
        self.assertEqual(res_excel.status_code, 200)
        self.assertIn("spreadsheetml.sheet", res_excel.content_type)
        self.assertGreater(len(res_excel.data), 100000)  # File size > 100KB

    def test_13_download_pdf_report(self):
        """Verify viewing/downloading the executive PDF engineering report."""
        res_pdf = self.client.get("/api/download-report-pdf")
        self.assertEqual(res_pdf.status_code, 200)
        self.assertIn("application/pdf", res_pdf.content_type)
        self.assertGreater(len(res_pdf.data), 50000)  # PDF size > 50KB

    def test_14_live_weather_endpoint(self):
        """Verify live real-time atmospheric synchronization API endpoint."""
        res = self.client.get("/api/weather/live?city=ahmedabad")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("city", data)
        self.assertIn("temperature", data)
        self.assertIn("humidity", data)
        self.assertIn("pressure", data)
        self.assertIn("wind_speed", data)
        self.assertIn("previous_rainfall", data)
        self.assertTrue(0 <= data["humidity"] <= 100)

    def test_15_domain_advisory_integration(self):
        """Verify Urban Flood Alert and Agricultural Advisory calculation."""
        payload = {
            "model": "random_forest",
            "temperature": 28.0,
            "humidity": 92.0,
            "pressure": 998.0,
            "wind_speed": 22.0,
            "previous_rainfall": 25.0
        }
        res = self.client.post("/api/predict", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("domain_advisory", data)
        advisory = data["domain_advisory"]
        self.assertIn("urban_flood", advisory)
        self.assertIn("agriculture", advisory)
        self.assertIn("level", advisory["urban_flood"])
        self.assertIn("irrigation_advice", advisory["agriculture"])
        self.assertIn("spray_status", advisory["agriculture"])

    def test_16_7day_forward_forecast(self):
        """Verify 7-day recursive forward forecast outlook simulation."""
        payload = {
            "temperature": 29.0,
            "humidity": 82.0,
            "pressure": 1006.0,
            "wind_speed": 16.0,
            "previous_rainfall": 12.0
        }
        res = self.client.post("/api/predict/7day-forecast", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["forecast_days"], 7)
        self.assertEqual(len(data["forecast"]), 7)
        for day in data["forecast"]:
            self.assertIn("day", day)
            self.assertIn("predicted_rainfall_mm", day)
            self.assertIn("rain_probability_pct", day)
            self.assertIn("weather_icon", day)
            self.assertIn("flood_risk", day)

    def test_17_batch_inference_and_download(self):
        """Verify batch CSV prediction and annotated CSV export."""
        sample_csv = (
            "date,temperature,humidity,pressure,wind_speed,previous_rainfall\n"
            "2024-07-01,28.5,88.0,1002.0,18.0,15.0\n"
            "2024-07-02,32.0,55.0,1012.0,12.0,0.0\n"
            "2024-07-03,26.0,94.0,996.0,24.0,45.0\n"
        )
        data = {
            "file": (io.BytesIO(sample_csv.encode("utf-8")), "monsoon_batch_test.csv")
        }
        res = self.client.post("/api/dataset/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        res_data = res.get_json()
        self.assertTrue(res_data["success"])
        self.assertEqual(res_data["rows"], 3)
        self.assertIn("batch_summary", res_data)
        self.assertEqual(res_data["batch_summary"]["total_rows"], 3)
        self.assertEqual(len(res_data["preview_records"]), 3)

        # Test downloading the annotated batch CSV
        res_download = self.client.get("/api/dataset/download-batch-result")
        self.assertEqual(res_download.status_code, 200)
        self.assertIn("text/csv", res_download.content_type)
        csv_text = res_download.data.decode("utf-8")
        self.assertIn("Predicted_Rainfall_RF_mm", csv_text)
        self.assertIn("Rain_Probability_Pct", csv_text)
        self.assertIn("Urban_Flood_Alert", csv_text)


if __name__ == "__main__":
    unittest.main()
