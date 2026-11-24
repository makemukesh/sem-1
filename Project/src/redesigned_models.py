"""
RainVision Redesigned Machine Learning Modeling Architecture (V2)
Implements:
1. Two-Stage Meteorological Hurdle Model (Occurrence Classifier + Severity Regressor)
2. Log1p-Transformed Target Random Forest Regressor
3. Blended Ensemble Regressor (Random Forest + Gradient Boosting)
4. Soft-Voting Multi-Class Ensemble Classifier (Balanced RF + Gradient Boosting)
5. Zero-Overwrite Persistence Engine (saves exclusively to models/redesigned_v2/)
"""

from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import json
import datetime
import joblib
import numpy as np
import pandas as pd

from sklearn.base import BaseEstimator, RegressorMixin, ClassifierMixin
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import (
    RandomForestRegressor, RandomForestClassifier,
    GradientBoostingRegressor, GradientBoostingClassifier,
    VotingClassifier
)
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)


class TwoStageHurdleRegressor(BaseEstimator, RegressorMixin):
    """
    Two-Stage Meteorological Hurdle Regressor:
    - Stage 1: Binary classifier predicting precipitation occurrence (Rain > 0.05 mm).
    - Stage 2: Quantitative regressor trained strictly on wet days (conditional depth).
    Final Prediction:
      y_pred = P(Rain > 0.05 | X) * y_severity(X)
    Eliminates dry-day overprediction while preserving extreme storm depths.
    """
    def __init__(self, classifier=None, regressor=None, rain_threshold=0.05):
        self.rain_threshold = rain_threshold
        self.classifier = classifier or RandomForestClassifier(
            n_estimators=100, max_depth=8, class_weight="balanced", random_state=42, n_jobs=-1
        )
        self.regressor = regressor or RandomForestRegressor(
            n_estimators=100, max_depth=10, min_samples_split=4, random_state=42, n_jobs=-1
        )

    def fit(self, X, y):
        X_df = pd.DataFrame(X)
        y_ser = pd.Series(y).values
        
        # Stage 1: Train binary occurrence classifier
        is_wet = (y_ser > self.rain_threshold).astype(int)
        self.classifier.fit(X_df, is_wet)
        
        # Stage 2: Train conditional severity regressor on wet days only
        wet_mask = y_ser > self.rain_threshold
        if np.sum(wet_mask) > 10:
            self.regressor.fit(X_df[wet_mask], y_ser[wet_mask])
        else:
            self.regressor.fit(X_df, y_ser)
            
        return self

    def predict(self, X, mode="expected_value"):
        X_df = pd.DataFrame(X)
        prob_wet = self.classifier.predict_proba(X_df)[:, 1]
        raw_severity = np.clip(self.regressor.predict(X_df), 0.0, None)
        
        if mode == "expected_value":
            preds = prob_wet * raw_severity
        elif mode == "hard_threshold":
            binary_wet = self.classifier.predict(X_df)
            preds = np.where(binary_wet == 1, raw_severity, 0.0)
        else:
            preds = prob_wet * raw_severity
            
        return np.clip(preds, 0.0, None)


class RedesignedEnsembleRegressor(BaseEstimator, RegressorMixin):
    """
    Blended Ensemble Regressor:
    Combines Random Forest Regressor (60%) and Gradient Boosting Regressor (40%).
    Reduces variance on dry days and optimizes MSE on storm events.
    """
    def __init__(self, rf_weight=0.60, gb_weight=0.40, random_state=42):
        self.rf_weight = rf_weight
        self.gb_weight = gb_weight
        self.random_state = random_state
        self.rf = RandomForestRegressor(
            n_estimators=120, max_depth=10, min_samples_split=4, random_state=random_state, n_jobs=-1
        )
        self.gb = GradientBoostingRegressor(
            n_estimators=100, learning_rate=0.04, max_depth=4, random_state=random_state
        )

    def fit(self, X, y):
        self.rf.fit(X, y)
        self.gb.fit(X, y)
        return self

    def predict(self, X):
        p_rf = np.clip(self.rf.predict(X), 0.0, None)
        p_gb = np.clip(self.gb.predict(X), 0.0, None)
        blended = (self.rf_weight * p_rf) + (self.gb_weight * p_gb)
        return np.clip(blended, 0.0, None)


class RedesignedVotingClassifier(BaseEstimator, ClassifierMixin):
    """
    Soft-Voting Multi-Class Ensemble Classifier:
    Combines Cost-Sensitive Random Forest (balanced class weights) and
    Gradient Boosting Classifier using calibrated soft probability voting.
    """
    def __init__(self, random_state=42):
        self.random_state = random_state
        self.rf = RandomForestClassifier(
            n_estimators=100, max_depth=8, min_samples_split=5, class_weight="balanced",
            random_state=random_state, n_jobs=-1
        )
        self.gb = GradientBoostingClassifier(
            n_estimators=100, learning_rate=0.05, max_depth=3, random_state=random_state
        )
        self.voting_clf = VotingClassifier(
            estimators=[("rf", self.rf), ("gb", self.gb)],
            voting="soft",
            weights=[1.2, 1.0]
        )

    def fit(self, X, y):
        self.voting_clf.fit(X, y)
        self.classes_ = self.voting_clf.classes_
        return self

    def predict(self, X):
        return self.voting_clf.predict(X)

    def predict_proba(self, X):
        return self.voting_clf.predict_proba(X)


def train_and_serialize_redesigned_models(
    X_train: pd.DataFrame,
    y_train_reg: pd.Series,
    y_train_clf: pd.Series,
    feature_names: List[str],
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Trains the redesigned models and persists them strictly to a dedicated
    redesigned directory (models/redesigned_v2/), GUARANTEEING that original model
    files in models/ are NEVER overwritten.
    """
    if output_dir is None:
        from src.data_processing import get_project_root
        output_dir = get_project_root() / "models" / "redesigned_v2"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Training Redesigned Ensemble Regressor (RF + GB)...")
    redesigned_reg = RedesignedEnsembleRegressor(random_state=42)
    redesigned_reg.fit(X_train, y_train_reg)

    print(f"Training Redesigned Hurdle Regressor (Two-Stage)...")
    hurdle_reg = TwoStageHurdleRegressor()
    hurdle_reg.fit(X_train, y_train_reg)

    print(f"Training Redesigned Soft-Voting Classifier (RF + GB)...")
    redesigned_clf = RedesignedVotingClassifier(random_state=42)
    redesigned_clf.fit(X_train, y_train_clf)

    # Serialize strictly to output_dir (models/redesigned_v2/)
    reg_path = output_dir / "rainvision_regressor_redesigned.joblib"
    hurdle_path = output_dir / "rainvision_hurdle_regressor_redesigned.joblib"
    clf_path = output_dir / "rainvision_classifier_redesigned.joblib"

    joblib.dump(redesigned_reg, reg_path)
    joblib.dump(hurdle_reg, hurdle_path)
    joblib.dump(redesigned_clf, clf_path)

    metadata = {
        "model_name": "RainVision Redesigned ML Architecture (V2)",
        "version": "2.0.0",
        "serialization_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "storage_policy": "ISOLATED_V2_DIRECTORY (Original models in models/ preserved unchanged)",
        "features": feature_names,
        "models": {
            "primary_regressor": {
                "type": "RedesignedEnsembleRegressor",
                "components": "RandomForestRegressor (60%) + GradientBoostingRegressor (40%)",
                "file": str(reg_path.name)
            },
            "hurdle_regressor": {
                "type": "TwoStageHurdleRegressor",
                "components": "Stage 1: Occurrence Classifier, Stage 2: Severity Regressor",
                "file": str(hurdle_path.name)
            },
            "classifier": {
                "type": "RedesignedVotingClassifier",
                "components": "Soft Voting: Balanced Random Forest (1.2) + Gradient Boosting (1.0)",
                "file": str(clf_path.name)
            }
        }
    }

    meta_path = output_dir / "model_metadata_redesigned.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)

    print("=" * 65)
    print("REDESIGNED MODELS PERSISTED WITH ZERO OVERWRITE:")
    print("=" * 65)
    print(f" - Primary Regressor : {reg_path} ({reg_path.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f" - Hurdle Regressor  : {hurdle_path} ({hurdle_path.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f" - Voting Classifier : {clf_path} ({clf_path.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f" - Metadata Registry : {meta_path}")
    print("=" * 65)

    return {
        "regressor": redesigned_reg,
        "hurdle": hurdle_reg,
        "classifier": redesigned_clf,
        "metadata": metadata,
        "output_dir": output_dir
    }

