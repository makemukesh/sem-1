"""
RainVision Model Training & Evaluation Module
Contains baseline models, regression suite, classification suite,
time-series cross-validation, hyperparameter tuning, and comprehensive metrics.
"""

from typing import Dict, Any, Tuple, List, Optional
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor, DummyClassifier
from sklearn.linear_model import LinearRegression, Ridge, LogisticRegression
from sklearn.tree import DecisionTreeRegressor, DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestRegressor, RandomForestClassifier,
    GradientBoostingRegressor, GradientBoostingClassifier
)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.inspection import permutation_importance


TIER_LABELS = ["No Rain", "Light", "Moderate", "Heavy"]


# =====================================================================
# 1. Regression Metrics & Evaluation
# =====================================================================

def evaluate_regression(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    model_name: str = "Model",
    clip_zero: bool = True
) -> Dict[str, Any]:
    """
    Evaluate regression predictions with meteorological metrics:
    - MAE: Mean Absolute Error (mm)
    - RMSE: Root Mean Squared Error (mm)
    - R²: Variance explained
    - Wet-Day MAE: Error specifically on days with observed rainfall > 0.05 mm
    """
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)

    if clip_zero:
        y_p = np.clip(y_p, 0.0, None)

    mae = float(mean_absolute_error(y_t, y_p))
    rmse = float(np.sqrt(mean_squared_error(y_t, y_p)))
    r2 = float(r2_score(y_t, y_p))

    # Calculate wet-day error (rainfall > 0.05 mm)
    wet_mask = y_t > 0.05
    if np.sum(wet_mask) > 0:
        wet_mae = float(mean_absolute_error(y_t[wet_mask], y_p[wet_mask]))
        wet_rmse = float(np.sqrt(mean_squared_error(y_t[wet_mask], y_p[wet_mask])))
    else:
        wet_mae = 0.0
        wet_rmse = 0.0

    return {
        "model": model_name,
        "mae": round(mae, 3),
        "rmse": round(rmse, 3),
        "r2": round(r2, 4),
        "wet_day_mae": round(wet_mae, 3),
        "wet_day_rmse": round(wet_rmse, 3)
    }


def train_regression_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    random_state: int = 42
) -> Dict[str, Any]:
    """
    Train a complete suite of regression models for rainfall amount prediction:
    1. Baseline Mean Regressor (Dummy)
    2. Linear Regression (OLS)
    3. Ridge Regression (Standardized)
    4. Decision Tree Regressor
    5. Random Forest Regressor
    6. Gradient Boosting Regressor
    """
    models = {
        "Baseline Mean": DummyRegressor(strategy="mean"),
        "Linear Regression": LinearRegression(),
        "Ridge Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=10.0, random_state=random_state))
        ]),
        "Decision Tree": DecisionTreeRegressor(max_depth=6, min_samples_split=10, random_state=random_state),
        "Random Forest": RandomForestRegressor(n_estimators=100, max_depth=10, min_samples_split=5, random_state=random_state, n_jobs=-1),
        "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=random_state)
    }

    trained_models = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        trained_models[name] = model

    return trained_models


# =====================================================================
# 2. Classification Metrics & Evaluation
# =====================================================================

def evaluate_classification(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    model_name: str = "Model",
    labels: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Evaluate classification predictions with multi-class metrics:
    - Accuracy
    - Macro Precision, Recall, F1
    - Weighted Precision, Recall, F1
    - Confusion Matrix
    """
    if labels is None:
        labels = TIER_LABELS

    acc = float(accuracy_score(y_true, y_pred))
    p_macro = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    r_macro = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    f1_macro = float(f1_score(y_true, y_pred, average="macro", zero_division=0))

    p_weighted = float(precision_score(y_true, y_pred, average="weighted", zero_division=0))
    r_weighted = float(recall_score(y_true, y_pred, average="weighted", zero_division=0))
    f1_weighted = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))

    cm = confusion_matrix(y_true, y_pred, labels=labels)

    return {
        "model": model_name,
        "accuracy": round(acc, 4),
        "precision_macro": round(p_macro, 4),
        "recall_macro": round(r_macro, 4),
        "f1_macro": round(f1_macro, 4),
        "precision_weighted": round(p_weighted, 4),
        "recall_weighted": round(r_weighted, 4),
        "f1_weighted": round(f1_weighted, 4),
        "confusion_matrix": cm
    }


def train_classification_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    random_state: int = 42
) -> Dict[str, Any]:
    """
    Train a complete suite of multi-class classification models:
    1. Baseline Majority Classifier (Dummy)
    2. Logistic Regression (Standardized + Balanced weights)
    3. Decision Tree Classifier (Balanced weights)
    4. Random Forest Classifier (Balanced weights)
    5. Gradient Boosting Classifier
    """
    models = {
        "Baseline Majority": DummyClassifier(strategy="most_frequent"),
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("logreg", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=random_state))
        ]),
        "Decision Tree": DecisionTreeClassifier(max_depth=6, min_samples_split=10, class_weight="balanced", random_state=random_state),
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=8, min_samples_split=5, class_weight="balanced", random_state=random_state, n_jobs=-1),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=3, random_state=random_state)
    }

    trained_models = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        trained_models[name] = model

    return trained_models


# =====================================================================
# 3. Time-Series Cross-Validation
# =====================================================================

def run_timeseries_cross_validation(
    model: Any,
    X: pd.DataFrame,
    y: pd.Series,
    n_splits: int = 5,
    is_classification: bool = False
) -> Dict[str, Any]:
    """
    Perform strictly forward-in-time cross-validation using TimeSeriesSplit.
    Each split uses an expanding historical window for training and evaluates
    on the immediate following temporal segment.
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)
    fold_scores = []

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
        X_v, y_v = X.iloc[val_idx], y.iloc[val_idx]

        model.fit(X_tr, y_tr)
        preds = model.predict(X_v)

        if is_classification:
            score = f1_score(y_v, preds, average="macro", zero_division=0)
            metric_name = "f1_macro"
        else:
            preds = np.clip(preds, 0.0, None)
            score = np.sqrt(mean_squared_error(y_v, preds))
            metric_name = "rmse"

        fold_scores.append(score)

    return {
        "n_splits": n_splits,
        "metric": metric_name,
        "fold_scores": [round(float(s), 4) for s in fold_scores],
        "mean_score": round(float(np.mean(fold_scores)), 4),
        "std_score": round(float(np.std(fold_scores)), 4)
    }


# =====================================================================
# 4. Hyperparameter Tuning
# =====================================================================

def tune_random_forest_regressor(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    n_splits: int = 4,
    random_state: int = 42
) -> Tuple[Any, Dict[str, Any]]:
    """
    Tune Random Forest Regressor using GridSearchCV constrained with TimeSeriesSplit.
    """
    param_grid = {
        "n_estimators": [50, 100, 150],
        "max_depth": [6, 10, 14],
        "min_samples_split": [2, 5, 10]
    }
    rf = RandomForestRegressor(random_state=random_state, n_jobs=-1)
    tscv = TimeSeriesSplit(n_splits=n_splits)
    grid = GridSearchCV(rf, param_grid, cv=tscv, scoring="neg_root_mean_squared_error", n_jobs=-1)
    grid.fit(X_train, y_train)

    return grid.best_estimator_, {
        "best_params": grid.best_params_,
        "best_cv_rmse": round(float(-grid.best_score_), 3)
    }


def tune_random_forest_classifier(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    n_splits: int = 4,
    random_state: int = 42
) -> Tuple[Any, Dict[str, Any]]:
    """
    Tune Random Forest Classifier using GridSearchCV constrained with TimeSeriesSplit.
    """
    param_grid = {
        "n_estimators": [50, 100, 150],
        "max_depth": [6, 8, 12],
        "min_samples_split": [2, 5, 10]
    }
    rfc = RandomForestClassifier(class_weight="balanced", random_state=random_state, n_jobs=-1)
    tscv = TimeSeriesSplit(n_splits=n_splits)
    grid = GridSearchCV(rfc, param_grid, cv=tscv, scoring="f1_macro", n_jobs=-1)
    grid.fit(X_train, y_train)

    return grid.best_estimator_, {
        "best_params": grid.best_params_,
        "best_cv_f1_macro": round(float(grid.best_score_), 4)
    }

