import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, accuracy_score, f1_score

train = pd.read_csv('data/processed/train.csv')
val = pd.read_csv('data/processed/val.csv')
test = pd.read_csv('data/processed/test.csv')

feats = [
    'temperature', 'humidity', 'pressure', 'wind_speed',
    'rain_lag_1', 'rain_lag_2', 'rain_lag_3',
    'rain_roll_mean_7', 'rain_roll_sum_7', 'rain_roll_max_7', 'rain_roll_mean_14',
    'temp_lag_1', 'humidity_lag_1', 'pressure_diff_1',
    'sin_day_of_year', 'cos_day_of_year', 'is_monsoon'
]

X_tr, y_tr_reg, y_tr_clf = train[feats], train['rainfall'], train['rainfall_category']
X_te, y_te_reg, y_te_clf = test[feats], test['rainfall'], test['rainfall_category']

# Linear & Ridge
ols = LinearRegression().fit(X_tr, y_tr_reg)
p_ols = np.clip(ols.predict(X_te), 0.0, None)
print(f"OLS: MAE={mean_absolute_error(y_te_reg, p_ols):.3f}, RMSE={np.sqrt(mean_squared_error(y_te_reg, p_ols)):.3f}, R2={r2_score(y_te_reg, p_ols):.4f}")

ridge_pipe = Pipeline([('scaler', StandardScaler()), ('ridge', Ridge(alpha=15.0, random_state=42))])
ridge_pipe.fit(X_tr, y_tr_reg)
p_ridge = np.clip(ridge_pipe.predict(X_te), 0.0, None)
print(f"Standardized Ridge: MAE={mean_absolute_error(y_te_reg, p_ridge):.3f}, RMSE={np.sqrt(mean_squared_error(y_te_reg, p_ridge)):.3f}, R2={r2_score(y_te_reg, p_ridge):.4f}")

# RF Regressor option 1 (default max_features)
rf1 = RandomForestRegressor(n_estimators=150, max_depth=10, min_samples_split=4, min_samples_leaf=2, random_state=42, n_jobs=-1).fit(X_tr, y_tr_reg)
p_rf1 = np.clip(rf1.predict(X_te), 0.0, None)
print(f"RF (all features): MAE={mean_absolute_error(y_te_reg, p_rf1):.3f}, RMSE={np.sqrt(mean_squared_error(y_te_reg, p_rf1)):.3f}, R2={r2_score(y_te_reg, p_rf1):.4f}")

# RF Regressor option 2 (max_features='sqrt')
rf2 = RandomForestRegressor(n_estimators=150, max_depth=12, min_samples_split=4, min_samples_leaf=2, max_features='sqrt', random_state=42, n_jobs=-1).fit(X_tr, y_tr_reg)
p_rf2 = np.clip(rf2.predict(X_te), 0.0, None)
print(f"RF (sqrt features): MAE={mean_absolute_error(y_te_reg, p_rf2):.3f}, RMSE={np.sqrt(mean_squared_error(y_te_reg, p_rf2)):.3f}, R2={r2_score(y_te_reg, p_rf2):.4f}")

# RF Classifier
rf_clf = RandomForestClassifier(n_estimators=150, max_depth=10, min_samples_split=4, class_weight='balanced', random_state=42, n_jobs=-1).fit(X_tr, y_tr_clf)
p_clf = rf_clf.predict(X_te)
print(f"RF Classifier: Acc={accuracy_score(y_te_clf, p_clf)*100:.2f}%, Macro F1={f1_score(y_te_clf, p_clf, average='macro'):.4f}, Weighted F1={f1_score(y_te_clf, p_clf, average='weighted'):.4f}")

