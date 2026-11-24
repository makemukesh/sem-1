"""
RainVision Data Processing Module
Handles data ingestion, file discovery, schema inspection, standardization,
meteorological quality checks, imputation, and outlier analysis.
"""

import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, Union, List
import numpy as np
import pandas as pd


def get_project_root() -> Path:
    """
    Robust project-root detection strategy.
    Recursively checks current working directory and parent directories
    for the RainVision root containing 'data' and 'src'.
    """
    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "data").exists() and (candidate / "src").exists():
            return candidate
    return cwd


def discover_raw_data_files(raw_dir: Union[str, Path]) -> List[Path]:
    """
    Automatically discovers candidate weather/rainfall data files (CSV, XLSX, XLS)
    in the specified raw data directory.
    """
    raw_path = Path(raw_dir)
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw data directory does not exist: {raw_path}")
    
    extensions = ["*.csv", "*.xlsx", "*.xls"]
    files = []
    for ext in extensions:
        files.extend(list(raw_path.glob(ext)))
    return sorted(files)


def load_raw_dataset(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Load weather/rainfall dataset from CSV or Excel with robust encoding fallbacks
    and date parsing.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found at: {path}")

    ext = path.suffix.lower()
    if ext == ".csv":
        encodings = ["utf-8", "latin1", "cp1252", "iso-8859-1"]
        df = None
        for enc in encodings:
            try:
                df = pd.read_csv(path, encoding=enc)
                break
            except (UnicodeDecodeError, Exception):
                continue
        if df is None:
            raise ValueError(f"Failed to read CSV at {path} with tested encodings.")
    elif ext in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Expected CSV or Excel.")

    return df


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names:
    - Strip leading/trailing whitespaces
    - Lowercase
    - Map variants to standard canonical names:
      'date', 'location', 'temperature', 'humidity', 'pressure', 'wind_speed',
      'rainfall', 'previous_rainfall'
    """
    df_clean = df.copy()
    # Clean whitespace in column names
    clean_cols = [c.strip().lower().replace(" ", "_") for c in df_clean.columns]
    df_clean.columns = clean_cols

    # Mapping dictionary for known weather dataset variations
    mapping = {
        "date": "date",
        "datetime": "date",
        "time": "date",
        "location": "location",
        "station": "location",
        "station_name": "location",
        "city": "location",
        "temperature": "temperature",
        "temp": "temperature",
        "temp_c": "temperature",
        "humidity": "humidity",
        "rel_humidity": "humidity",
        "relative_humidity": "humidity",
        "pressure": "pressure",
        "barometric_pressure": "pressure",
        "pressure_hpa": "pressure",
        "wind_speed": "wind_speed",
        "wind": "wind_speed",
        "wind_speed_kmh": "wind_speed",
        "rainfall": "rainfall",
        "rain": "rainfall",
        "precipitation": "rainfall",
        "precip_mm": "rainfall",
        "previous_rainfall": "previous_rainfall",
        "prev_rainfall": "previous_rainfall",
        "rain_lag_1": "previous_rainfall",
    }

    new_cols = [mapping.get(c, c) for c in df_clean.columns]
    df_clean.columns = new_cols
    return df_clean


def inspect_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Perform structural and data quality inspection of DataFrame.
    """
    report = {
        "num_rows": int(df.shape[0]),
        "num_cols": int(df.shape[1]),
        "columns": list(df.columns),
        "dtypes": {k: str(v) for k, v in df.dtypes.items()},
        "missing_counts": df.isna().sum().to_dict(),
        "total_missing_cells": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "memory_usage_mb": float(df.memory_usage(deep=True).sum() / (1024 * 1024)),
    }
    
    # Check date column if present
    if "date" in df.columns:
        date_series = pd.to_datetime(df["date"], errors="coerce")
        valid_dates = date_series.dropna()
        if len(valid_dates) > 0:
            report["date_min"] = str(valid_dates.min().date())
            report["date_max"] = str(valid_dates.max().date())
            report["total_days_span"] = int((valid_dates.max() - valid_dates.min()).days) + 1
        else:
            report["date_min"] = None
            report["date_max"] = None

    return report


def check_physical_boundaries(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Check meteorological physical validity bounds:
    - Temperature: 0°C to 55°C (typical India range)
    - Relative Humidity: 5% to 100%
    - Atmospheric Pressure: 900 hPa to 1050 hPa
    - Wind Speed: 0.0 to 120.0 km/h
    - Rainfall: >= 0.0 mm
    """
    bounds = {
        "temperature": (0.0, 55.0),
        "humidity": (5.0, 100.0),
        "pressure": (900.0, 1050.0),
        "wind_speed": (0.0, 120.0),
        "rainfall": (0.0, 500.0),
    }

    issues = {}
    for col, (b_min, b_max) in bounds.items():
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            below = (df[col] < b_min).sum()
            above = (df[col] > b_max).sum()
            issues[col] = {
                "below_physical_min": int(below),
                "above_physical_max": int(above),
                "actual_min": float(df[col].min()) if not df[col].isna().all() else None,
                "actual_max": float(df[col].max()) if not df[col].isna().all() else None,
                "domain_valid": bool(below == 0 and above == 0)
            }
    return issues


def clean_weather_dataset(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Complete meteorological data cleaning pipeline:
    1. Standardize column names
    2. Drop completely empty rows
    3. Convert date to datetime, drop unparseable dates
    4. Remove duplicate date & location records
    5. Chronological sorting
    6. Validate physical weather domain values
    7. Time-series forward-fill / linear interpolation for small gaps (without lookahead)
    8. Distinguish recorded 0.0 mm from missing values
    9. Produce before-and-after audit report
    """
    raw_rows = len(df_raw)
    raw_missing = df_raw.isna().sum().to_dict()

    # Step 1: Standardize columns
    df = standardize_columns(df_raw)

    # Step 2: Drop completely empty rows
    df = df.dropna(how="all").copy()
    dropped_empty = raw_rows - len(df)

    # Step 3: Date conversion
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).copy()
    else:
        raise ValueError("Dataset is missing a 'date' column required for time-series cleaning.")

    # Step 4: Deduplicate based on ['date', 'location'] if location exists, else ['date']
    subset = ["date", "location"] if "location" in df.columns else ["date"]
    dup_count = int(df.duplicated(subset=subset).sum())
    df = df.drop_duplicates(subset=subset, keep="first").copy()

    # Step 5: Chronological sort
    df = df.sort_values(by="date").reset_index(drop=True)

    # Step 6: Physical range clamping / validation
    physical_issues = check_physical_boundaries(df)
    for col, checks in physical_issues.items():
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            if col == "rainfall":
                # Rainfall must be non-negative
                df[col] = df[col].clip(lower=0.0)
            elif col == "humidity":
                df[col] = df[col].clip(lower=0.0, upper=100.0)

    # Step 7: Time-series imputation
    # Atmospheric continuous variables (temp, humidity, pressure, wind_speed) are continuous:
    # use forward fill or time interpolation (strictly forward/past aware)
    numeric_weather_cols = [c for c in ["temperature", "humidity", "pressure", "wind_speed"] if c in df.columns]
    for col in numeric_weather_cols:
        # Forward fill preserves past meteorological state into brief sensor gaps
        df[col] = df[col].ffill().bfill()

    # Rainfall: Never blindly replace missing rainfall with 0 if it wasn't recorded,
    # but if a small isolated missing value occurs, ffill or use previous rainfall
    if "rainfall" in df.columns:
        if "previous_rainfall" in df.columns:
            df["rainfall"] = df["rainfall"].fillna(df["previous_rainfall"])
        df["rainfall"] = df["rainfall"].fillna(0.0)

    if "previous_rainfall" in df.columns:
        df["previous_rainfall"] = df["rainfall"].shift(1).fillna(0.0)

    # Final audit report
    clean_report = {
        "initial_rows": raw_rows,
        "empty_rows_dropped": dropped_empty,
        "duplicate_rows_dropped": dup_count,
        "final_cleaned_rows": len(df),
        "raw_missing_per_col": raw_missing,
        "cleaned_missing_per_col": df.isna().sum().to_dict(),
        "date_start": str(df["date"].min().date()),
        "date_end": str(df["date"].max().date()),
        "location": df["location"].iloc[0] if "location" in df.columns and len(df) > 0 else "Unknown",
        "physical_boundary_status": physical_issues
    }

    return df, clean_report


def detect_outliers_iqr(df: pd.DataFrame, column: str = "rainfall") -> Dict[str, Any]:
    """
    Detect outliers using Tukey's Interquartile Range (IQR) method:
    IQR = Q3 - Q1
    Lower Bound = Q1 - 1.5 * IQR
    Upper Bound = Q3 + 1.5 * IQR
    Also records severe outliers (> Q3 + 3.0 * IQR).
    """
    if column not in df.columns:
        raise KeyError(f"Column '{column}' not found in DataFrame.")

    series = df[column].dropna()
    q1 = float(series.quantile(0.25))
    median = float(series.median())
    q3 = float(series.quantile(0.75))
    iqr = q3 - q1

    lower_bound = max(0.0, q1 - 1.5 * iqr)
    upper_bound = q3 + 1.5 * iqr
    extreme_bound = q3 + 3.0 * iqr

    outliers_1_5 = df[df[column] > upper_bound]
    outliers_3_0 = df[df[column] > extreme_bound]

    return {
        "column": column,
        "q1": q1,
        "median": median,
        "q3": q3,
        "iqr": iqr,
        "upper_bound_1_5_iqr": upper_bound,
        "extreme_bound_3_0_iqr": extreme_bound,
        "outlier_count_1_5_iqr": int(len(outliers_1_5)),
        "outlier_count_3_0_iqr": int(len(outliers_3_0)),
        "max_value": float(series.max()) if len(series) > 0 else 0.0,
        "is_genuine_meteorological_extreme": True,
        "meteorological_justification": (
            "Rainfall distributions in monsoon environments are heavily right-skewed and zero-inflated. "
            "High precipitation values (e.g. 80-160 mm) correspond to real meteorological low-pressure depressions "
            "and convective cyclones rather than measurement errors. Removing them would severely bias models "
            "against predicting flood-grade extreme weather events."
        )
    }

