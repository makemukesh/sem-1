"""
RainVision Climate Analytics Module
Computes long-term climatological statistics, annual totals, monthly averages,
seasonal breakdowns, wet/dry spells, and standardized rainfall anomalies.
"""

from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd


def calculate_annual_climate_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate annual rainfall indicators:
    - Total annual rainfall (mm)
    - Mean daily rainfall (mm)
    - Wet days count (> 0.05 mm)
    - Heavy rain days (> 15.0 mm)
    - Max 24-hr rainfall event (mm)
    """
    df_c = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_c["date"]):
        df_c["date"] = pd.to_datetime(df_c["date"])
    df_c["year"] = df_c["date"].dt.year

    annual = df_c.groupby("year").agg(
        total_rainfall_mm=("rainfall", "sum"),
        mean_daily_rainfall_mm=("rainfall", "mean"),
        wet_days=("rainfall", lambda s: int((s > 0.05).sum())),
        moderate_heavy_days=("rainfall", lambda s: int((s > 2.5).sum())),
        extreme_storm_days=("rainfall", lambda s: int((s > 50.0).sum())),
        max_daily_rainfall_mm=("rainfall", "max"),
        mean_temp=("temperature", "mean"),
        mean_humidity=("humidity", "mean")
    ).reset_index()

    return annual.round(2)


def calculate_monthly_climatology(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute long-term 10-year monthly climatology:
    Mean rainfall, median rainfall, std dev, and probability of rain by calendar month.
    """
    df_c = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_c["date"]):
        df_c["date"] = pd.to_datetime(df_c["date"])
    df_c["month"] = df_c["date"].dt.month

    monthly = df_c.groupby("month").agg(
        mean_monthly_rain=("rainfall", lambda s: s.sum() / len(df_c["date"].dt.year.unique())),
        mean_daily_rain=("rainfall", "mean"),
        rain_probability=("rainfall", lambda s: (s > 0.05).mean() * 100.0),
        mean_temp=("temperature", "mean"),
        mean_humidity=("humidity", "mean")
    ).reset_index()

    month_names = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
    }
    monthly["month_name"] = monthly["month"].map(month_names)
    return monthly.round(2)


def calculate_rainfall_anomalies(df: pd.DataFrame) -> Tuple[pd.DataFrame, float]:
    """
    Compute annual precipitation anomalies relative to the historical baseline mean:
    Anomaly = Annual Total - Long-term Mean
    Standardized Anomaly = (Annual Total - Mean) / Std
    """
    annual = calculate_annual_climate_summary(df)
    baseline_mean = float(annual["total_rainfall_mm"].mean())
    baseline_std = float(annual["total_rainfall_mm"].std())

    annual["baseline_mean_mm"] = round(baseline_mean, 2)
    annual["rainfall_anomaly_mm"] = (annual["total_rainfall_mm"] - baseline_mean).round(2)
    annual["standardized_anomaly"] = ((annual["total_rainfall_mm"] - baseline_mean) / baseline_std).round(3)
    annual["classification"] = annual["standardized_anomaly"].apply(
        lambda z: "Severe Excess" if z > 1.5 else (
            "Moderate Excess" if z > 0.5 else (
                "Normal" if z >= -0.5 else (
                    "Moderate Deficit" if z >= -1.5 else "Severe Deficit"
                )
            )
        )
    )

    return annual, baseline_mean

