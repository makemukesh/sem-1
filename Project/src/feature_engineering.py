"""
RainVision Feature Engineering Module
Builds calendar, cyclical, autoregressive lag, rolling window, and atmospheric
rate-of-change features for rainfall prediction without temporal data leakage.
Also creates classification target labels according to meteorological standards.
"""

from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import pandas as pd


# Meteorological intensity classification tiers (IMD / WMO standard)
TIER_THRESHOLDS = {
    "no_rain_max": 0.05,
    "light_max": 2.5,
    "moderate_max": 15.0
}


def get_season(month: int) -> str:
    """
    Classify calendar month into meteorological season for South Asian / Gujarat climate:
    - Winter: Dec, Jan, Feb
    - Pre-Monsoon (Summer): Mar, Apr, May
    - Monsoon (Southwest Monsoon): Jun, Jul, Aug, Sep
    - Post-Monsoon (Autumn/Retreating): Oct, Nov
    """
    if month in [3, 4, 5]:
        return "Summer"
    elif month in [6, 7, 8, 9]:
        return "Monsoon"
    elif month in [10, 11]:
        return "Post-Monsoon"
    else:
        return "Winter"


def categorize_rainfall(amount_mm: float) -> str:
    """
    Categorize rainfall depth (in millimeters) into meteorological intensity tiers:
    - No Rain: <= 0.05 mm (trace or dry)
    - Light: 0.05 mm < x <= 2.5 mm
    - Moderate: 2.5 mm < x <= 15.0 mm
    - Heavy: > 15.0 mm
    """
    if amount_mm is None or np.isnan(amount_mm):
        return "No Rain"
    if amount_mm <= TIER_THRESHOLDS["no_rain_max"]:
        return "No Rain"
    elif amount_mm <= TIER_THRESHOLDS["light_max"]:
        return "Light"
    elif amount_mm <= TIER_THRESHOLDS["moderate_max"]:
        return "Moderate"
    else:
        return "Heavy"


def create_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract calendar and cyclical features from datetime:
    - month, day, day_of_year, year, season, is_monsoon
    - sin_day_of_year, cos_day_of_year (cyclical annual representation)
    """
    df_feat = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_feat["date"]):
        df_feat["date"] = pd.to_datetime(df_feat["date"])

    dates = df_feat["date"]
    df_feat["month"] = dates.dt.month
    df_feat["day"] = dates.dt.day
    df_feat["day_of_year"] = dates.dt.dayofyear
    df_feat["year"] = dates.dt.year
    df_feat["season"] = df_feat["month"].apply(get_season)
    df_feat["is_monsoon"] = df_feat["month"].apply(lambda m: 1 if m in [6, 7, 8, 9] else 0)

    # Cyclical trigonometric encodings
    doy = df_feat["day_of_year"]
    df_feat["sin_day_of_year"] = np.sin(2 * np.pi * doy / 365.25)
    df_feat["cos_day_of_year"] = np.cos(2 * np.pi * doy / 365.25)

    return df_feat


def create_lag_and_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create autoregressive rainfall lags, rolling statistics, and atmospheric rate-of-change.
    All features strictly use past observations (shift) to eliminate target leakage:
    - rain_lag_1, rain_lag_2, rain_lag_3
    - rain_roll_mean_7, rain_roll_sum_7, rain_roll_max_7, rain_roll_mean_14
    - temp_lag_1, humidity_lag_1, pressure_diff_1
    """
    df_feat = df.copy()
    
    # 1. Autoregressive Rainfall Lags (Previous Days)
    df_feat["rain_lag_1"] = df_feat["rainfall"].shift(1)
    df_feat["rain_lag_2"] = df_feat["rainfall"].shift(2)
    df_feat["rain_lag_3"] = df_feat["rainfall"].shift(3)

    # 2. Rolling Window Rainfall Statistics (based on past rainfall up to t-1)
    # Using shift(1) ensures the rolling window strictly summarizes antecedent conditions
    shifted_rain = df_feat["rainfall"].shift(1)
    df_feat["rain_roll_mean_7"] = shifted_rain.rolling(window=7, min_periods=7).mean()
    df_feat["rain_roll_sum_7"] = shifted_rain.rolling(window=7, min_periods=7).sum()
    df_feat["rain_roll_max_7"] = shifted_rain.rolling(window=7, min_periods=7).max()
    df_feat["rain_roll_mean_14"] = shifted_rain.rolling(window=14, min_periods=14).mean()

    # 3. Atmospheric Lags & Differencing
    if "temperature" in df_feat.columns:
        df_feat["temp_lag_1"] = df_feat["temperature"].shift(1)
    if "humidity" in df_feat.columns:
        df_feat["humidity_lag_1"] = df_feat["humidity"].shift(1)
    if "pressure" in df_feat.columns:
        # Pressure drop indicates incoming cyclonic depressions / storm fronts
        df_feat["pressure_diff_1"] = df_feat["pressure"] - df_feat["pressure"].shift(1)

    return df_feat


def build_complete_features(df_clean: pd.DataFrame, drop_na: bool = True) -> pd.DataFrame:
    """
    End-to-end feature pipeline:
    1. Calendar & cyclical encodings
    2. Autoregressive lags & rolling windows
    3. Classification target generation
    4. Safe dropping of initial NA rows created by lag windows (14 rows)
    """
    df = df_clean.copy()
    df = create_calendar_features(df)
    df = create_lag_and_rolling_features(df)
    
    # Classification target tier
    df["rainfall_category"] = df["rainfall"].apply(categorize_rainfall)

    if drop_na:
        # The 14-day rolling window creates 14 initial NaN rows
        initial_len = len(df)
        df = df.dropna().reset_index(drop=True)
        dropped_rows = initial_len - len(df)
    
    return df


def get_model_feature_columns() -> List[str]:
    """
    Returns the canonical ordered list of input features used across all ML models.
    """
    return [
        "temperature",
        "humidity",
        "pressure",
        "wind_speed",
        "rain_lag_1",
        "rain_lag_2",
        "rain_lag_3",
        "rain_roll_mean_7",
        "rain_roll_sum_7",
        "rain_roll_max_7",
        "rain_roll_mean_14",
        "temp_lag_1",
        "humidity_lag_1",
        "pressure_diff_1",
        "sin_day_of_year",
        "cos_day_of_year",
        "is_monsoon"
    ]


def split_timeseries_chronological(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split time-series dataset strictly forward in time (chronological order):
    - Train: First 70%
    - Validation: Next 15%
    - Test: Final 15% (unseen future period)
    Ensures zero temporal data leakage.
    """
    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    train_df = df.iloc[:train_end].copy().reset_index(drop=True)
    val_df = df.iloc[train_end:val_end].copy().reset_index(drop=True)
    test_df = df.iloc[val_end:].copy().reset_index(drop=True)

    return train_df, val_df, test_df

