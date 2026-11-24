"""
RainVision: An Intelligent Rainfall Forecasting, Prediction, and Climate Analytics Platform
Package Initialization
"""

from .data_processing import (
    get_project_root,
    discover_raw_data_files,
    load_raw_dataset,
    standardize_columns,
    inspect_dataset,
    clean_weather_dataset,
    detect_outliers_iqr
)

from .feature_engineering import (
    get_season,
    categorize_rainfall,
    create_calendar_features,
    create_lag_and_rolling_features,
    build_complete_features,
    get_model_feature_columns,
    split_timeseries_chronological
)

from .model_training import (
    evaluate_regression,
    train_regression_models,
    evaluate_classification,
    train_classification_models,
    run_timeseries_cross_validation,
    tune_random_forest_regressor,
    tune_random_forest_classifier
)

from .prediction import (
    load_rainvision_models,
    validate_weather_inputs,
    prepare_prediction_features,
    predict_rainfall_amount,
    predict_rainfall_category,
    predict_weather
)

from .climate_analytics import (
    calculate_annual_climate_summary,
    calculate_monthly_climatology,
    calculate_rainfall_anomalies
)

