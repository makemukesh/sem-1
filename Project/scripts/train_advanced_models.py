"""
Train Advanced Models for RainVision:
1. Gradient Boosting Regressor
2. Two-Stage Meteorological Hurdle Model (Rain Probability Classifier + Wet-Day Severity Regressor)
Evaluates on test.csv and saves clean joblib artifacts.
"""

from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

BASE_DIR = Path("D:/sem=1")
TRAIN_PATH = BASE_DIR / "Project" / "data" / "processed" / "train.csv"
TEST_PATH = BASE_DIR / "Project" / "data" / "processed" / "test.csv"
WEBSITE_MODELS_DIR = BASE_DIR / "Website" / "models"
PROJECT_MODELS_DIR = BASE_DIR / "Project" / "models"

FEATURE_COLUMNS = [
    "temperature", "humidity", "pressure", "wind_speed",
    "rain_lag_1", "rain_lag_2", "rain_lag_3",
    "rain_roll_mean_7", "rain_roll_sum_7", "rain_roll_max_7", "rain_roll_mean_14",
    "temp_lag_1", "humidity_lag_1", "pressure_diff_1",
    "sin_day_of_year", "cos_day_of_year", "is_monsoon"
]


class HurdleRainfallModel:
    """
    Two-Stage Meteorological Hurdle Model:
    Stage 1: Predicts precipitation occurrence probability P(Rain > 0.05mm).
    Stage 2: Predicts quantitative precipitation depth conditioned on wet days.
    """
    def __init__(self, classifier=None, regressor=None, rain_threshold=0.05):
        self.rain_threshold = rain_threshold
        self.classifier = classifier or RandomForestClassifier(
            n_estimators=120, max_depth=7, class_weight="balanced", random_state=42
        )
        self.regressor = regressor or RandomForestRegressor(
            n_estimators=120, max_depth=8, min_samples_split=4, random_state=42
        )

    def fit(self, X, y):
        X_df = pd.DataFrame(X, columns=FEATURE_COLUMNS) if not isinstance(X, pd.DataFrame) else X
        y_ser = pd.Series(y).values

        # Stage 1: Rain occurrence binary
        is_wet = (y_ser > self.rain_threshold).astype(int)
        self.classifier.fit(X_df, is_wet)

        # Stage 2: Severity on wet days only
        wet_mask = y_ser > self.rain_threshold
        if wet_mask.sum() > 10:
            self.regressor.fit(X_df[wet_mask], y_ser[wet_mask])
        else:
            self.regressor.fit(X_df, y_ser)
        return self

    def predict_proba(self, X):
        X_df = pd.DataFrame(X, columns=FEATURE_COLUMNS) if not isinstance(X, pd.DataFrame) else X
        probs = self.classifier.predict_proba(X_df)
        return probs[:, 1] if probs.shape[1] > 1 else np.zeros(len(X_df))

    def predict(self, X):
        X_df = pd.DataFrame(X, columns=FEATURE_COLUMNS) if not isinstance(X, pd.DataFrame) else X
        p_wet = self.predict_proba(X_df)
        severity = np.clip(self.regressor.predict(X_df), 0.0, None)
        # Hurdle zero-projection: if probability < 0.28, set to 0.0; otherwise p * severity
        preds = np.where(p_wet >= 0.28, p_wet * severity, 0.0)
        return np.round(np.clip(preds, 0.0, None), 2)


def main():
    print("[1/4] Loading training and test data...")
    train_df = pd.read_csv(TRAIN_PATH)
    test_df = pd.read_csv(TEST_PATH)

    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df["rainfall"].values

    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df["rainfall"].values

    print(f"  Training samples: {len(X_train):,}, Test samples: {len(X_test):,}")

    # 1. Train Gradient Boosting Regressor
    print("\n[2/4] Training Gradient Boosting Regressor...")
    gb = GradientBoostingRegressor(
        n_estimators=140,
        learning_rate=0.08,
        max_depth=5,
        subsample=0.85,
        random_state=42
    )
    gb.fit(X_train, y_train)

    p_gb = np.clip(gb.predict(X_test), 0.0, None)
    r2_gb = r2_score(y_test, p_gb)
    mae_gb = mean_absolute_error(y_test, p_gb)
    rmse_gb = np.sqrt(mean_squared_error(y_test, p_gb))
    print(f"  Gradient Boosting -> R2: {r2_gb:.4f}, MAE: {mae_gb:.3f} mm, RMSE: {rmse_gb:.3f} mm")

    # 2. Train Two-Stage Hurdle Model
    print("\n[3/4] Training Two-Stage Meteorological Hurdle Model...")
    hurdle = HurdleRainfallModel()
    hurdle.fit(X_train, y_train)

    p_hurdle = hurdle.predict(X_test)
    r2_h = r2_score(y_test, p_hurdle)
    mae_h = mean_absolute_error(y_test, p_hurdle)
    rmse_h = np.sqrt(mean_squared_error(y_test, p_hurdle))
    print(f"  Two-Stage Hurdle -> R2: {r2_h:.4f}, MAE: {mae_h:.3f} mm, RMSE: {rmse_h:.3f} mm")

    # 3. Save artifacts
    print("\n[4/4] Saving model artifacts to Website and Project directories...")
    WEBSITE_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    PROJECT_MODELS_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(gb, WEBSITE_MODELS_DIR / "gradient_boosting_model.joblib")
    joblib.dump(hurdle, WEBSITE_MODELS_DIR / "hurdle_model.joblib")

    joblib.dump(gb, PROJECT_MODELS_DIR / "gradient_boosting_model.joblib")
    joblib.dump(hurdle, PROJECT_MODELS_DIR / "hurdle_model.joblib")

    print(f"  Saved gradient_boosting_model.joblib to {WEBSITE_MODELS_DIR}")
    print(f"  Saved hurdle_model.joblib to {WEBSITE_MODELS_DIR}")
    print("\nTraining and evaluation completed successfully!")


if __name__ == "__main__":
    main()

