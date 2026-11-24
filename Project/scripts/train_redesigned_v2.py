"""
Script to train and persist RainVision Redesigned ML models into models/redesigned_v2/
Ensures zero overwrite of existing model files in models/.
"""
from pathlib import Path
import pandas as pd
import sys

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.redesigned_models import train_and_serialize_redesigned_models

def main():
    train_path = ROOT / "data" / "processed" / "train.csv"
    if not train_path.exists():
        raise FileNotFoundError(f"Missing train data at {train_path}")

    train_df = pd.read_csv(train_path)
    
    feature_cols = [
        "temperature", "humidity", "pressure", "wind_speed",
        "rain_lag_1", "rain_lag_2", "rain_lag_3",
        "rain_roll_mean_7", "rain_roll_sum_7", "rain_roll_max_7", "rain_roll_mean_14",
        "temp_lag_1", "humidity_lag_1", "pressure_diff_1",
        "sin_day_of_year", "cos_day_of_year", "is_monsoon"
    ]
    
    X_train = train_df[feature_cols]
    y_train_reg = train_df["rainfall"]
    y_train_clf = train_df["rainfall_category"]
    
    print(f"Loaded training data: {X_train.shape[0]} rows, {len(feature_cols)} features.")
    res = train_and_serialize_redesigned_models(
        X_train=X_train,
        y_train_reg=y_train_reg,
        y_train_clf=y_train_clf,
        feature_names=feature_cols,
        output_dir=ROOT / "models" / "redesigned_v2"
    )
    print("Training and serialization completed successfully.")

if __name__ == "__main__":
    main()

