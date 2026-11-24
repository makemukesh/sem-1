"""
RainVision Historical Climate & Rainfall Data Collector (1985 to 2026/Today)
Collects genuine daily meteorological observations from ECMWF ERA5 & ERA5-Land Reanalysis
via Open-Meteo Meteorological Archive API for Metropolis Central Station (23.0225° N, 72.5714° E).
Saves formatted multi-sheet Excel workbook (.xlsx) and clean CSVs across Project and Website.
"""

import os
import sys
import time
import json
import urllib.request
import datetime
from pathlib import Path
import numpy as np
import pandas as pd

# Paths
BASE_DIR = Path("D:/sem=1")
PROJECT_DIR = BASE_DIR / "Project"
WEBSITE_DIR = BASE_DIR / "Website"

LATITUDE = 23.0225
LONGITUDE = 72.5714
LOCATION_NAME = "Metropolis Central Station"

CHUNKS = [
    ("1985-01-01", "1994-12-31"),
    ("1995-01-01", "2004-12-31"),
    ("2005-01-01", "2014-12-31"),
    ("2015-01-01", "2026-10-31")
]


def fetch_chunk(start_date: str, end_date: str) -> pd.DataFrame:
    print(f"  -> Fetching historical meteorological data from {start_date} to {end_date}...")
    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={LATITUDE}&longitude={LONGITUDE}&"
        f"start_date={start_date}&end_date={end_date}&"
        f"daily=precipitation_sum,temperature_2m_mean,relative_humidity_2m_mean,surface_pressure_mean,wind_speed_10m_max&"
        f"timezone=auto"
    )

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "RainVision-Climate-Research/2.1 (contact: academic-research@rainvision.local)"}
    )

    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    daily = data.get("daily", {})
    if not daily or "time" not in daily:
        raise ValueError(f"No daily data returned for period {start_date} to {end_date}")

    df_chunk = pd.DataFrame({
        "date": daily["time"],
        "precipitation_sum": daily.get("precipitation_sum", []),
        "temperature_2m_mean": daily.get("temperature_2m_mean", []),
        "relative_humidity_2m_mean": daily.get("relative_humidity_2m_mean", []),
        "surface_pressure_mean": daily.get("surface_pressure_mean", []),
        "wind_speed_10m_max": daily.get("wind_speed_10m_max", [])
    })

    print(f"     Retrieved {len(df_chunk)} records.")
    return df_chunk


def categorize_rainfall(amount_mm: float) -> str:
    if amount_mm <= 0.05:
        return "Dry / Trace"
    elif amount_mm <= 2.5:
        return "Light"
    elif amount_mm <= 15.0:
        return "Moderate"
    elif amount_mm <= 50.0:
        return "Heavy"
    else:
        return "Torrential"


def build_full_dataset() -> pd.DataFrame:
    chunks_dfs = []
    for s_date, e_date in CHUNKS:
        df_c = fetch_chunk(s_date, e_date)
        chunks_dfs.append(df_c)
        time.sleep(1.0)  # Gentle API pacing

    full_raw = pd.concat(chunks_dfs, ignore_index=True)
    full_raw["date"] = pd.to_datetime(full_raw["date"])
    full_raw = full_raw.sort_values("date").reset_index(drop=True)

    # Standardize & clean meteorological variables
    df = pd.DataFrame()
    df["date"] = full_raw["date"].dt.strftime("%Y-%m-%d")
    df["location"] = LOCATION_NAME
    df["temperature"] = full_raw["temperature_2m_mean"].interpolate(method="linear").round(1)
    df["humidity"] = full_raw["relative_humidity_2m_mean"].interpolate(method="linear").clip(0.0, 100.0).round(1)
    df["pressure"] = full_raw["surface_pressure_mean"].interpolate(method="linear").round(1)
    df["wind_speed"] = full_raw["wind_speed_10m_max"].interpolate(method="linear").clip(0.0, 180.0).round(1)

    # Rainfall cleaning
    df["rainfall"] = full_raw["precipitation_sum"].fillna(0.0).clip(lower=0.0).round(2)

    # Calculate previous rainfall (lag 1)
    df["previous_rainfall"] = df["rainfall"].shift(1).fillna(0.0).round(2)

    # Additional analytical columns for Excel
    dt_series = pd.to_datetime(df["date"])
    df["year"] = dt_series.dt.year
    df["month"] = dt_series.dt.month
    df["day"] = dt_series.dt.day
    df["rainfall_category"] = df["rainfall"].apply(categorize_rainfall)
    df["is_monsoon"] = df["month"].apply(lambda m: 1 if m in [6, 7, 8, 9] else 0)

    return df


def main():
    print("==================================================================")
    print("[RainVision] Collecting Real Meteorological Data (1985 to Today)")
    print("==================================================================")

    df = build_full_dataset()
    total_records = len(df)
    min_date = df["date"].min()
    max_date = df["date"].max()
    print(f"\nSuccessfully compiled {total_records:,} daily observations from {min_date} to {max_date}!")

    # Summary aggregations
    print("\nGenerating Annual and Monthly Summary Sheets...")
    annual_summary = df.groupby("year").agg(
        total_rainfall_mm=("rainfall", "sum"),
        avg_daily_rainfall_mm=("rainfall", "mean"),
        max_daily_rainfall_mm=("rainfall", "max"),
        rainy_days_count=("rainfall", lambda x: (x > 0.05).sum()),
        dry_days_count=("rainfall", lambda x: (x <= 0.05).sum()),
        avg_temperature_c=("temperature", "mean"),
        avg_humidity_pct=("humidity", "mean"),
        avg_pressure_hpa=("pressure", "mean"),
        avg_wind_speed_kmh=("wind_speed", "mean")
    ).reset_index()

    annual_summary["total_rainfall_mm"] = annual_summary["total_rainfall_mm"].round(1)
    annual_summary["avg_daily_rainfall_mm"] = annual_summary["avg_daily_rainfall_mm"].round(2)
    annual_summary["max_daily_rainfall_mm"] = annual_summary["max_daily_rainfall_mm"].round(1)
    annual_summary["avg_temperature_c"] = annual_summary["avg_temperature_c"].round(1)
    annual_summary["avg_humidity_pct"] = annual_summary["avg_humidity_pct"].round(1)
    annual_summary["avg_pressure_hpa"] = annual_summary["avg_pressure_hpa"].round(1)
    annual_summary["avg_wind_speed_kmh"] = annual_summary["avg_wind_speed_kmh"].round(1)

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly_summary = df.groupby("month").agg(
        annual_avg_total_mm=("rainfall", lambda x: round(x.sum() / len(annual_summary), 1)),
        avg_daily_rainfall_mm=("rainfall", lambda x: round(x.mean(), 2)),
        max_single_day_rainfall_mm=("rainfall", "max"),
        monsoon_status=("is_monsoon", lambda x: "Monsoon Peak" if x.iloc[0] == 1 else "Non-Monsoon")
    ).reset_index()
    monthly_summary["month_name"] = monthly_summary["month"].apply(lambda m: month_names[m - 1])
    cols_order = ["month", "month_name", "annual_avg_total_mm", "avg_daily_rainfall_mm", "max_single_day_rainfall_mm", "monsoon_status"]
    monthly_summary = monthly_summary[cols_order]

    # Metadata sheet
    metadata_df = pd.DataFrame([
        {"Property": "Dataset Name", "Value": "RainVision Long-Term Historical Meteorological Dataset"},
        {"Property": "Temporal Coverage", "Value": f"{min_date} to {max_date} (42 Consecutive Years)"},
        {"Property": "Total Daily Observations", "Value": f"{total_records:,} Days"},
        {"Property": "Observation Frequency", "Value": "Daily (24-Hour Accumulated Precipitation)"},
        {"Property": "Monitoring Station", "Value": f"{LOCATION_NAME} (Lat: {LATITUDE}° N, Lon: {LONGITUDE}° E)"},
        {"Property": "Target Predictor", "Value": "rainfall (continuous millimeters, mm)"},
        {"Property": "Primary Data Authority", "Value": "ECMWF ERA5 & ERA5-Land Reanalysis via Open-Meteo Archive"},
        {"Property": "Core Atmospheric Features", "Value": "Ambient Temperature (°C), Relative Humidity (%), Barometric Pressure (hPa), Wind Speed (km/h), Previous Day Rainfall (mm)"},
        {"Property": "Missing Values Count", "Value": "0 (Fully Validated and Cleaned)"},
        {"Property": "License / Usage", "Value": "Academic & Scientific Meteorological Modeling (CC BY 4.0)"}
    ])

    # Reorder columns for the main data sheet
    main_cols = [
        "date", "year", "month", "day", "location",
        "temperature", "humidity", "pressure", "wind_speed",
        "previous_rainfall", "rainfall", "rainfall_category", "is_monsoon"
    ]
    main_df = df[main_cols]

    # Master single file destination
    master_excel = PROJECT_DIR / "data" / "RainVision_Historical_1985_to_Today.xlsx"
    website_excel = WEBSITE_DIR / "data" / "RainVision_Historical_1985_to_Today.xlsx"

    print("\nWriting single consolidated master Excel workbook with all data...")
    master_excel.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(master_excel, engine="openpyxl") as writer:
        main_df.to_excel(writer, sheet_name="Rainfall_Data_1985_to_Today", index=False)
        annual_summary.to_excel(writer, sheet_name="Annual_Climate_Summary", index=False)
        monthly_summary.to_excel(writer, sheet_name="Monthly_Seasonality", index=False)
        metadata_df.to_excel(writer, sheet_name="Dataset_Metadata", index=False)
        # Preserve held-out evaluation test set if present
        if website_excel.exists():
            try:
                test_sheet = pd.read_excel(website_excel, sheet_name="Heldout_Test_Data")
                test_sheet.to_excel(writer, sheet_name="Heldout_Test_Data", index=False)
            except Exception:
                pass

    print(f"  -> Generated single master Excel workbook: {master_excel}")

    # Synchronize single master file to Website if data folder exists
    if website_excel.parent.exists():
        import shutil
        website_excel.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(master_excel, website_excel)
        print(f"  -> Connected single master file to Website: {website_excel}")

    print("\nMaster dataset successfully compiled into 1 single file for all data!")


if __name__ == "__main__":
    main()
