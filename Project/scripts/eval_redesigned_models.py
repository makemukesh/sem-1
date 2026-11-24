from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, GradientBoostingRegressor, GradientBoostingClassifier, VotingClassifier
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, accuracy_score, f1_score

from src.redesigned_models import TwoStageHurdleRegressor, RedesignedEnsembleRegressor, RedesignedVotingClassifier

ROOT = Path("D:/Project")
train_df = pd.read_csv(ROOT / "data" / "processed" / "train.csv")
val_df = pd.read_csv(ROOT / "data" / "processed" / "val.csv")
test_df = pd.read_csv(ROOT / "data" / "processed" / "test.csv")

feature_cols = [
    "temperature", "humidity", "pressure", "wind_speed",
    "rain_lag_1", "rain_lag_2", "rain_lag_3",
    "rain_roll_mean_7", "rain_roll_sum_7", "rain_roll_max_7", "rain_roll_mean_14",
    "temp_lag_1", "humidity_lag_1", "pressure_diff_1",
    "sin_day_of_year", "cos_day_of_year", "is_monsoon"
]

X_tr, y_tr_reg, y_tr_clf = train_df[feature_cols], train_df["rainfall"], train_df["rainfall_category"]
X_te, y_te_reg, y_te_clf = test_df[feature_cols], test_df["rainfall"], test_df["rainfall_category"]

print("--- REGRESSION MODELS ---")
# 1. OLS
ols = LinearRegression().fit(X_tr, y_tr_reg)
p_ols = np.clip(ols.predict(X_te), 0.0, None)
print(f"OLS: MAE={mean_absolute_error(y_te_reg, p_ols):.3f}, RMSE={np.sqrt(mean_squared_error(y_te_reg, p_ols)):.3f}, R2={r2_score(y_te_reg, p_ols):.4f}")

# 2. RF
rf = RandomForestRegressor(n_estimators=100, max_depth=10, min_samples_split=5, random_state=42, n_jobs=-1).fit(X_tr, y_tr_reg)
p_rf = np.clip(rf.predict(X_te), 0.0, None)
print(f"RF : MAE={mean_absolute_error(y_te_reg, p_rf):.3f}, RMSE={np.sqrt(mean_squared_error(y_te_reg, p_rf)):.3f}, R2={r2_score(y_te_reg, p_rf):.4f}")

# 3. Hurdle
hurdle = TwoStageHurdleRegressor().fit(X_tr, y_tr_reg)
p_hurdle = hurdle.predict(X_te, mode="expected_value")
print(f"Hurdle: MAE={mean_absolute_error(y_te_reg, p_hurdle):.3f}, RMSE={np.sqrt(mean_squared_error(y_te_reg, p_hurdle)):.3f}, R2={r2_score(y_te_reg, p_hurdle):.4f}")

# Dry-day MAE (rainfall <= 0.05 mm)
dry_mask = y_te_reg <= 0.05
print(f"Dry days count: {np.sum(dry_mask)} of {len(y_te_reg)}")
print(f" - OLS dry-day MAE   : {mean_absolute_error(y_te_reg[dry_mask], p_ols[dry_mask]):.3f} mm")
print(f" - RF dry-day MAE    : {mean_absolute_error(y_te_reg[dry_mask], p_rf[dry_mask]):.3f} mm")
print(f" - Hurdle dry-day MAE: {mean_absolute_error(y_te_reg[dry_mask], p_hurdle[dry_mask]):.3f} mm")

# 4. Blended Ensemble
ensemble = RedesignedEnsembleRegressor(random_state=42).fit(X_tr, y_tr_reg)
p_ens = ensemble.predict(X_te)
print(f"Ensemble: MAE={mean_absolute_error(y_te_reg, p_ens):.3f}, RMSE={np.sqrt(mean_squared_error(y_te_reg, p_ens)):.3f}, R2={r2_score(y_te_reg, p_ens):.4f}")

print("\n--- CLASSIFICATION MODELS ---")
rf_clf = RandomForestClassifier(n_estimators=100, max_depth=8, min_samples_split=5, class_weight="balanced", random_state=42, n_jobs=-1).fit(X_tr, y_tr_clf)
p_clf_rf = rf_clf.predict(X_te)
print(f"RF Clf : Acc={accuracy_score(y_te_clf, p_clf_rf):.4f}, Macro F1={f1_score(y_te_clf, p_clf_rf, average='macro'):.4f}, Weighted F1={f1_score(y_te_clf, p_clf_rf, average='weighted'):.4f}")

voting_clf = RedesignedVotingClassifier(random_state=42).fit(X_tr, y_tr_clf)
p_clf_ens = voting_clf.predict(X_te)
print(f"Voting : Acc={accuracy_score(y_te_clf, p_clf_ens):.4f}, Macro F1={f1_score(y_te_clf, p_clf_ens, average='macro'):.4f}, Weighted F1={f1_score(y_te_clf, p_clf_ens, average='weighted'):.4f}")

