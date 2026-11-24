"""
RainVision - Report Asset Builder
Reproduces the latest project pipeline (80/20 chronological split, 17 features)
and regenerates all metrics + figures used in the M.Sc. IT project report.
"""
import json, time, warnings
from pathlib import Path
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.dummy import DummyRegressor, DummyClassifier
from sklearn.linear_model import LinearRegression, Ridge, LogisticRegression
from sklearn.tree import DecisionTreeRegressor, DecisionTreeClassifier
from sklearn.ensemble import (RandomForestRegressor, RandomForestClassifier,
                              GradientBoostingRegressor, GradientBoostingClassifier)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (mean_absolute_error, mean_squared_error, r2_score,
                             accuracy_score, precision_score, recall_score, f1_score,
                             confusion_matrix, classification_report)
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV

ROOT = Path(r"D:\sem=1\Project")
OUT_FIG = ROOT / "outputs" / "report_figures"
OUT_REP = ROOT / "outputs" / "report_data"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_REP.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.labelsize": 10, "axes.grid": True, "grid.alpha": 0.3,
    "figure.dpi": 200, "savefig.dpi": 200, "savefig.bbox": "tight",
})
PALETTE = ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728", "#9467bd", "#8c564b"]

DATA = ROOT / "data" / "RainVision_Historical_1985_to_Today.xlsx"
df_raw = pd.read_excel(DATA, sheet_name="Rainfall_Data_1985_to_Today")
df_raw["date"] = pd.to_datetime(df_raw["date"])
df_raw = df_raw.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)

# ------------------------------------------------------------------
# Feature engineering (identical to the production notebook)
# ------------------------------------------------------------------
def categorize(y):
    if y <= 0.05: return "Dry / Trace"
    elif y <= 2.5: return "Light"
    elif y <= 15.0: return "Moderate"
    elif y <= 50.0: return "Heavy"
    else: return "Torrential"

def prepare(df_in):
    df = df_in.copy()
    doy = df["date"].dt.dayofyear
    df["sin_day_of_year"] = np.sin(2*np.pi*doy/365.25)
    df["cos_day_of_year"] = np.cos(2*np.pi*doy/365.25)
    df["rain_lag_1"] = df["rainfall"].shift(1).fillna(0.0)
    df["rain_lag_2"] = df["rainfall"].shift(2).fillna(0.0)
    df["rain_lag_3"] = df["rainfall"].shift(3).fillna(0.0)
    df["rain_roll_mean_7"] = df["rainfall"].shift(1).rolling(7, min_periods=1).mean().fillna(0.0)
    df["rain_roll_sum_7"] = df["rainfall"].shift(1).rolling(7, min_periods=1).sum().fillna(0.0)
    df["rain_roll_max_7"] = df["rainfall"].shift(1).rolling(7, min_periods=1).max().fillna(0.0)
    df["rain_roll_mean_14"] = df["rainfall"].shift(1).rolling(14, min_periods=1).mean().fillna(0.0)
    df["temp_lag_1"] = df["temperature"].shift(1).bfill()
    df["humidity_lag_1"] = df["humidity"].shift(1).bfill()
    df["pressure_diff_1"] = (df["pressure"] - df["pressure"].shift(1)).fillna(0.0)
    df["is_monsoon"] = df["date"].dt.month.isin([6,7,8,9]).astype(int)
    df["rainfall_category"] = df["rainfall"].apply(categorize)
    df["month_name"] = df["date"].dt.strftime("%b")
    df["year"] = df["date"].dt.year
    return df

df = prepare(df_raw)

FEATURES = ["temperature","humidity","pressure","wind_speed",
            "rain_lag_1","rain_lag_2","rain_lag_3",
            "rain_roll_mean_7","rain_roll_sum_7","rain_roll_max_7","rain_roll_mean_14",
            "temp_lag_1","humidity_lag_1","pressure_diff_1",
            "sin_day_of_year","cos_day_of_year","is_monsoon"]
CATEGORIES = ["Dry / Trace","Light","Moderate","Heavy","Torrential"]

split = int(len(df)*0.80)
train, test = df.iloc[:split].copy(), df.iloc[split:].copy()
X_tr, y_tr, c_tr = train[FEATURES], train["rainfall"], train["rainfall_category"]
X_te, y_te, c_te = test[FEATURES], test["rainfall"], test["rainfall_category"]

# ------------------------------------------------------------------
# EDA statistics
# ------------------------------------------------------------------
r = df["rainfall"]
stats = {
    "rows": int(len(df)), "cols": int(df_raw.shape[1] - 1),
    "start": str(df["date"].min().date()), "end": str(df["date"].max().date()),
    "years": int(df["date"].dt.year.nunique()),
    "station": str(df["location"].iloc[0]),
    "missing": int(df_raw.isna().sum().sum()),
    "duplicates": int(df_raw.duplicated(subset=["date"]).sum()),
    "rain_mean": round(float(r.mean()),2), "rain_median": round(float(r.median()),2),
    "rain_std": round(float(r.std()),2), "rain_max": round(float(r.max()),2),
    "rain_p95": round(float(r.quantile(.95)),2), "rain_p99": round(float(r.quantile(.99)),2),
    "dry_days": int((r <= 0.05).sum()), "dry_pct": round(float((r <= 0.05).mean()*100),2),
    "wet_days": int((r > 0.05).sum()), "wet_pct": round(float((r > 0.05).mean()*100),2),
    "annual_mean": round(float(df.groupby("year")["rainfall"].sum().mean()),1),
    "monsoon_share": round(float(df[df["is_monsoon"]==1]["rainfall"].sum()/r.sum()*100),2),
    "temp_min": round(float(df.temperature.min()),1), "temp_max": round(float(df.temperature.max()),1),
    "hum_min": round(float(df.humidity.min()),1), "hum_max": round(float(df.humidity.max()),1),
    "press_min": round(float(df.pressure.min()),1), "press_max": round(float(df.pressure.max()),1),
    "wind_min": round(float(df.wind_speed.min()),1), "wind_max": round(float(df.wind_speed.max()),1),
    "train_rows": int(len(train)), "test_rows": int(len(test)),
    "train_start": str(train.date.min().date()), "train_end": str(train.date.max().date()),
    "test_start": str(test.date.min().date()), "test_end": str(test.date.max().date()),
}
cat_counts = df["rainfall_category"].value_counts().reindex(CATEGORIES).fillna(0).astype(int)
stats["category_counts"] = {k:int(v) for k,v in cat_counts.items()}
stats["category_pct"] = {k: round(float(v/len(df)*100),2) for k,v in cat_counts.items()}
monthly = df.groupby(df["date"].dt.month)["rainfall"].agg(["mean","sum"])
annual = df.groupby("year")["rainfall"].agg(["sum","mean","max"])
corr = df[["rainfall","temperature","humidity","pressure","wind_speed"]].corr()["rainfall"].round(3).to_dict()
stats["target_corr"] = {k: float(v) for k,v in corr.items()}
stats["monthly_top"] = monthly["sum"].sort_values(ascending=False).head(3).round(0).to_dict()
stats["annual_min"] = round(float(annual["sum"].min()),1)
stats["annual_max"] = round(float(annual["sum"].max()),1)
stats["annual_mean_total"] = round(float(annual["sum"].mean()),1)
stats["annual_std_total"] = round(float(annual["sum"].std()),1)
stats["prev_equals_rain"] = bool(np.allclose(df_raw["previous_rainfall"].values, df_raw["rainfall"].values))

# ------------------------------------------------------------------
# FIGURE 1: rainfall time series + annual totals
# ------------------------------------------------------------------
fig, ax = plt.subplots(2,1, figsize=(11,7))
ax[0].plot(df["date"], df["rainfall"], color="#1f77b4", lw=0.4, alpha=0.8)
ax[0].plot(df["date"], df["rainfall"].rolling(365, min_periods=30).mean(), color="#d62728", lw=1.6, label="365-day moving average")
ax[0].set_title("Daily Rainfall Time Series (1985-2026)")
ax[0].set_ylabel("Rainfall (mm)"); ax[0].legend(loc="upper right")
ax[1].bar(annual.index, annual["sum"], color="#2ca02c", edgecolor="black", lw=0.4)
ax[1].axhline(annual["sum"].mean(), color="#d62728", ls="--", lw=1.5, label=f"Mean = {annual['sum'].mean():.0f} mm")
ax[1].set_title("Annual Total Rainfall"); ax[1].set_xlabel("Year"); ax[1].set_ylabel("Annual Rainfall (mm)")
ax[1].legend()
plt.tight_layout(); plt.savefig(OUT_FIG/"fig1_timeseries_annual.png"); plt.close()

# ------------------------------------------------------------------
# FIGURE 2: distribution + zero inflation + monthly climatology
# ------------------------------------------------------------------
fig, ax = plt.subplots(1,3, figsize=(15,4.6))
sns.histplot(r[r>0], bins=60, ax=ax[0], color="#1f77b4")
ax[0].set_title("Distribution of Wet-Day Rainfall"); ax[0].set_xlabel("Rainfall (mm)")
ax[0].set_ylabel("Frequency")
labels = ["Dry / Trace", "Light", "Moderate", "Heavy", "Torrential"]
sizes = cat_counts.values
colors = ["#95a5a6","#3498db","#f1c40f","#e67e22","#c0392b"]
wedges, txt, autotxt = ax[1].pie(sizes, labels=labels, autopct="%1.1f%%", colors=colors,
                                 startangle=90, textprops={"fontsize":9})
ax[1].set_title("Rainfall Intensity Class Distribution")
m_order = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
mmean = df.groupby(df["date"].dt.strftime("%b"))["rainfall"].mean().reindex(m_order)
sns.barplot(x=mmean.index, y=mmean.values, ax=ax[2], palette="Blues_d")
ax[2].set_title("Mean Daily Rainfall by Month"); ax[2].set_xlabel("Month"); ax[2].set_ylabel("Mean Rainfall (mm)")
plt.tight_layout(); plt.savefig(OUT_FIG/"fig2_distribution_seasonality.png"); plt.close()

# ------------------------------------------------------------------
# FIGURE 3: correlation heatmap + bivariate
# ------------------------------------------------------------------
fig, ax = plt.subplots(1,2, figsize=(13,5))
cdf = df[["rainfall","temperature","humidity","pressure","wind_speed",
          "rain_lag_1","rain_roll_mean_7","pressure_diff_1"]].copy()
cdf.columns = ["Rainfall","Temperature","Humidity","Pressure","Wind","Rain Lag-1","7-day Mean","Pressure Diff"]
sns.heatmap(cdf.corr(), annot=True, fmt=".2f", cmap="RdBu_r", center=0,
            ax=ax[0], cbar_kws={"shrink":.8}, annot_kws={"size":8})
ax[0].set_title("Correlation Matrix of Meteorological Variables")
vars_ = [("humidity","Humidity (%)"),("pressure","Pressure (hPa)"),
         ("temperature","Temperature (\u00b0C)"),("wind_speed","Wind Speed (km/h)")]
colors_ = ["#2980b9","#c0392b","#e67e22","#27ae60"]
for i,(col,lab) in enumerate(vars_):
    a = ax[1].inset_axes([0, 0, 0, 0]) if False else None
plt.tight_layout(); plt.savefig(OUT_FIG/"fig3_correlation.png"); plt.close()

fig, axes = plt.subplots(2,2, figsize=(12,8))
for a,(col,lab),c in zip(axes.ravel(), vars_, colors_):
    a.scatter(df[col], df["rainfall"], s=6, alpha=0.25, color=c, edgecolors="none")
    a.set_xlabel(lab); a.set_ylabel("Rainfall (mm)"); a.set_title(f"Rainfall vs {lab.split(' (')[0]}")
    # binned mean
    bins = pd.qcut(df[col], 20, duplicates="drop")
    bm = df.groupby(bins, observed=True)["rainfall"].mean()
    centers = [iv.mid for iv in bm.index]
    a.plot(centers, bm.values, color="black", lw=2, marker="o", ms=3, label="Binned mean")
    a.legend(fontsize=8)
plt.tight_layout(); plt.savefig(OUT_FIG/"fig4_bivariate.png"); plt.close()

# ------------------------------------------------------------------
# MODEL TRAINING
# ------------------------------------------------------------------
def reg_metrics(y_true, y_pred):
    y_p = np.clip(np.asarray(y_pred, float), 0, None)
    y_t = np.asarray(y_true, float)
    wet = y_t > 0.05
    return {
        "MAE": round(float(mean_absolute_error(y_t,y_p)),3),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_t,y_p))),3),
        "R2": round(float(r2_score(y_t,y_p)),4),
        "WetMAE": round(float(mean_absolute_error(y_t[wet],y_p[wet])),3),
        "DryMAE": round(float(mean_absolute_error(y_t[~wet],y_p[~wet])),3),
        "Bias": round(float(np.mean(y_p-y_t)),3),
    }

def clf_metrics(y_true, y_pred):
    return {
        "Accuracy": round(float(accuracy_score(y_true,y_pred)),4),
        "MacroPrecision": round(float(precision_score(y_true,y_pred,average="macro",zero_division=0)),4),
        "MacroRecall": round(float(recall_score(y_true,y_pred,average="macro",zero_division=0)),4),
        "MacroF1": round(float(f1_score(y_true,y_pred,average="macro",zero_division=0)),4),
        "WeightedF1": round(float(f1_score(y_true,y_pred,average="weighted",zero_division=0)),4),
    }

models = {
    "Baseline Mean": DummyRegressor(strategy="mean"),
    "Linear Regression (OLS)": LinearRegression(),
    "Ridge Regression": Pipeline([("scaler",StandardScaler()),("ridge",Ridge(alpha=10.0,random_state=42))]),
    "Decision Tree": DecisionTreeRegressor(max_depth=6,min_samples_split=10,random_state=42),
    "Random Forest": RandomForestRegressor(n_estimators=100,max_depth=10,min_samples_split=5,random_state=42,n_jobs=-1),
    "Gradient Boosting": GradientBoostingRegressor(n_estimators=100,learning_rate=0.05,max_depth=4,random_state=42),
}
reg_rows, trained = [], {}
for name,m in models.items():
    t0=time.time(); m.fit(X_tr,y_tr); p=m.predict(X_te)
    row={"Model":name, **reg_metrics(y_te,p), "TrainTime":round(time.time()-t0,2)}
    reg_rows.append(row); trained[name]=m

# persistence baseline
p_pers = X_te["rain_lag_1"].values
reg_rows.insert(1, {"Model":"Baseline Persistence (Lag-1)", **reg_metrics(y_te,p_pers), "TrainTime":0.0})

# Hurdle model
t0=time.time()
gate = RandomForestClassifier(n_estimators=100,max_depth=8,class_weight="balanced",random_state=42,n_jobs=-1)
gate.fit(X_tr,(y_tr>0.05).astype(int))
wetm = y_tr>0.05
amt = RandomForestRegressor(n_estimators=100,max_depth=10,min_samples_split=5,random_state=42,n_jobs=-1)
amt.fit(X_tr[wetm],y_tr[wetm])
g_pred = gate.predict(X_te); a_pred = np.clip(amt.predict(X_te),0,None)
p_hurdle = np.where(g_pred==1,a_pred,0.0)
reg_rows.append({"Model":"Two-Stage Hurdle Model", **reg_metrics(y_te,p_hurdle), "TrainTime":round(time.time()-t0,2)})

# Probability-weighted hurdle variant (for comparison)
p_prob = gate.predict_proba(X_te)[:,1]*a_pred

reg_df = pd.DataFrame(reg_rows).sort_values("R2",ascending=False).reset_index(drop=True)
print(reg_df.to_string())

clf_models = {
    "Baseline Majority": DummyClassifier(strategy="most_frequent"),
    "Logistic Regression": Pipeline([("scaler",StandardScaler()),("clf",LogisticRegression(max_iter=1000,class_weight="balanced",random_state=42))]),
    "Decision Tree": DecisionTreeClassifier(max_depth=6,min_samples_split=10,class_weight="balanced",random_state=42),
    "Random Forest": RandomForestClassifier(n_estimators=100,max_depth=8,min_samples_split=5,class_weight="balanced",random_state=42,n_jobs=-1),
    "Gradient Boosting": GradientBoostingClassifier(n_estimators=100,learning_rate=0.05,max_depth=3,random_state=42),
}
clf_rows, trained_clf = [], {}
for name,m in clf_models.items():
    m.fit(X_tr,c_tr); p=m.predict(X_te)
    clf_rows.append({"Model":name, **clf_metrics(c_te,p)}); trained_clf[name]=m
clf_df = pd.DataFrame(clf_rows).sort_values("MacroF1",ascending=False).reset_index(drop=True)
print(clf_df.to_string())

# per class report for RF
rf_report = classification_report(c_te, trained_clf["Random Forest"].predict(X_te), output_dict=True, zero_division=0)
per_class = {k: {kk: round(float(vv),3) for kk,vv in v.items()} for k,v in rf_report.items() if k in CATEGORIES}

# ------------------------------------------------------------------
# FIG 5: regression comparison
# ------------------------------------------------------------------
fig, ax = plt.subplots(1,2, figsize=(14,5))
order = reg_df.sort_values("R2")
ax[0].barh(order["Model"], order["R2"], color=["#95a5a6" if x<0 else "#2ca02c" for x in order["R2"]])
ax[0].set_title("R\u00b2 Score by Regression Model"); ax[0].set_xlabel("R\u00b2 (higher is better)")
for i,v in enumerate(order["R2"]): ax[0].text(v+0.005 if v>0 else 0.005, i, f"{v:.3f}", va="center", fontsize=8)
order2 = reg_df.sort_values("MAE", ascending=False)
ax[1].barh(order2["Model"], order2["MAE"], color="#e67e22")
ax[1].set_title("Mean Absolute Error by Regression Model"); ax[1].set_xlabel("MAE (mm, lower is better)")
for i,v in enumerate(order2["MAE"]): ax[1].text(v+0.03, i, f"{v:.3f}", va="center", fontsize=8)
plt.tight_layout(); plt.savefig(OUT_FIG/"fig5_regression_comparison.png"); plt.close()

# FIG 6: actual vs predicted + residuals for best tree models
rf_pred = np.clip(trained["Random Forest"].predict(X_te),0,None)
fig, axes = plt.subplots(2,2, figsize=(12,10))
for a,(pred,title) in zip(axes[0], [(rf_pred,"Random Forest"),(p_hurdle,"Two-Stage Hurdle Model")]):
    a.scatter(y_te,pred,s=8,alpha=.35,color="#1f77b4",edgecolors="none")
    mv=max(float(y_te.max()),float(pred.max()))
    a.plot([0,mv],[0,mv],"r--",lw=1.5,label="Ideal 1:1")
    a.set_title(f"{title}: Actual vs Predicted (R\u00b2 = {r2_score(y_te,pred):.3f})")
    a.set_xlabel("Actual Rainfall (mm)"); a.set_ylabel("Predicted Rainfall (mm)"); a.legend()
for a,(pred,title) in zip(axes[1], [(rf_pred,"Random Forest"),(p_hurdle,"Two-Stage Hurdle Model")]):
    res = y_te-pred
    a.scatter(pred,res,s=8,alpha=.35,color="#e67e22",edgecolors="none")
    a.axhline(0,color="black",ls="--",lw=1)
    a.set_title(f"{title}: Residual Plot"); a.set_xlabel("Predicted (mm)"); a.set_ylabel("Residual (mm)")
plt.tight_layout(); plt.savefig(OUT_FIG/"fig6_actual_vs_predicted_residuals.png"); plt.close()

# FIG 7: dry-day behaviour (zero inflation)
fig, ax = plt.subplots(1,2, figsize=(13,4.8))
dry = y_te <= 0.05
vals = [np.mean(rf_pred[dry]), np.mean(p_hurdle[dry]), np.mean(np.clip(trained["Linear Regression (OLS)"].predict(X_te),0,None)[dry])]
names = ["Random Forest","Hurdle","OLS"]
bars = ax[0].bar(names, vals, color=["#2980b9","#27ae60","#c0392b"])
ax[0].set_title("Mean Predicted Rainfall on Dry Days (False-Rain Check)")
ax[0].set_ylabel("Mean predicted mm (ideal = 0)")
for b,v in zip(bars,vals): ax[0].text(b.get_x()+b.get_width()/2, v+0.01, f"{v:.3f}", ha="center", fontsize=9)
ax[1].hist([y_te[dry], rf_pred[dry], p_hurdle[dry]], bins=20, label=["Actual","RF","Hurdle"],
           color=["black","#2980b9","#27ae60"], alpha=.7)
ax[1].set_title("Distribution of Predictions on Dry Days"); ax[1].set_xlabel("Rainfall (mm)"); ax[1].legend()
plt.tight_layout(); plt.savefig(OUT_FIG/"fig7_dry_day_check.png"); plt.close()

# FIG 8: 90-day timeline
fig, ax = plt.subplots(figsize=(13,4.8))
s = test.iloc[-90:].reset_index(drop=True)
Xs = s[FEATURES]
ax.plot(s["date"], s["rainfall"], color="black", lw=2, label="Actual")
ax.plot(s["date"], np.clip(trained["Random Forest"].predict(Xs),0,None), color="#27ae60", ls="--", lw=1.6, label="Random Forest")
ax.plot(s["date"], np.clip(trained["Linear Regression (OLS)"].predict(Xs),0,None), color="#e74c3c", ls=":", lw=1.6, label="Linear Regression")
gate_s = gate.predict(Xs); amt_s=np.clip(amt.predict(Xs),0,None)
ax.plot(s["date"], np.where(gate_s==1,amt_s,0), color="#8e44ad", ls="-.", lw=1.6, label="Hurdle")
ax.set_title("90-Day Held-Out Forecast Timeline Comparison")
ax.set_xlabel("Date"); ax.set_ylabel("Rainfall (mm)"); ax.legend(); plt.xticks(rotation=45)
plt.tight_layout(); plt.savefig(OUT_FIG/"fig8_timeline.png"); plt.close()

# FIG 9: classification comparison + confusion matrix
fig, ax = plt.subplots(1,2, figsize=(14,5))
co = clf_df.sort_values("MacroF1")
metrics_cols = ["Accuracy","MacroPrecision","MacroRecall","MacroF1"]
x = np.arange(len(co)); w=0.2
for i,col in enumerate(metrics_cols):
    ax[0].barh(x+(i-1.5)*w, co[col], height=w, label=col)
ax[0].set_yticks(x); ax[0].set_yticklabels(co["Model"], fontsize=8)
ax[0].set_title("Classification Performance Comparison"); ax[0].set_xlabel("Score"); ax[0].legend(fontsize=7)
cm = confusion_matrix(c_te, trained_clf["Random Forest"].predict(X_te), labels=CATEGORIES)
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax[1],
            xticklabels=CATEGORIES, yticklabels=CATEGORIES, cbar=False)
ax[1].set_title("Random Forest Confusion Matrix"); ax[1].set_xlabel("Predicted"); ax[1].set_ylabel("Actual")
plt.setp(ax[1].get_xticklabels(), rotation=30, ha="right", fontsize=8)
plt.setp(ax[1].get_yticklabels(), rotation=0, fontsize=8)
plt.tight_layout(); plt.savefig(OUT_FIG/"fig9_classification.png"); plt.close()

# FIG 10: feature importance
rfm = trained["Random Forest"]
imp = pd.Series(rfm.feature_importances_, index=FEATURES).sort_values(ascending=True)
gbr = trained["Gradient Boosting"]
imp_gb = pd.Series(gbr.feature_importances_, index=FEATURES).reindex(imp.index)
fig, ax = plt.subplots(figsize=(9,6.5))
ax.barh(imp.index, imp.values, label="Random Forest (MDI)", color="#2980b9")
ax.plot(imp_gb.values, imp.index, "o", color="#e67e22", label="Gradient Boosting")
ax.set_title("Feature Importance (Impurity-Based)"); ax.set_xlabel("Relative Importance"); ax.legend()
plt.tight_layout(); plt.savefig(OUT_FIG/"fig10_feature_importance.png"); plt.close()

# ------------------------------------------------------------------
# 5-fold TimeSeriesSplit CV on Random Forest
# ------------------------------------------------------------------
print("Running TimeSeriesSplit CV ...")
tscv = TimeSeriesSplit(n_splits=5)
cv_rows = []
for i,(tr_idx,va_idx) in enumerate(tscv.split(df[FEATURES])):
    m = RandomForestRegressor(n_estimators=100,max_depth=10,min_samples_split=5,random_state=42,n_jobs=-1)
    m.fit(df[FEATURES].iloc[tr_idx], df["rainfall"].iloc[tr_idx])
    p = np.clip(m.predict(df[FEATURES].iloc[va_idx]),0,None)
    cv_rows.append({"Fold":f"Fold {i+1}","TrainSize":len(tr_idx),"ValSize":len(va_idx),
                    "R2":round(float(r2_score(df['rainfall'].iloc[va_idx],p)),4),
                    "RMSE":round(float(np.sqrt(mean_squared_error(df['rainfall'].iloc[va_idx],p))),3),
                    "MAE":round(float(mean_absolute_error(df['rainfall'].iloc[va_idx],p)),3)})
cv_df = pd.DataFrame(cv_rows)
print(cv_df.to_string())

fig, ax = plt.subplots(1,2, figsize=(13,4.4))
ax[0].plot(cv_df["Fold"], cv_df["R2"], marker="o", color="#2980b9", lw=2, label="Fold R\u00b2")
ax[0].axhline(cv_df["R2"].mean(), color="#d62728", ls="--", label=f"Mean = {cv_df['R2'].mean():.3f}")
ax[0].set_title("5-Fold Expanding-Window Temporal Cross-Validation"); ax[0].set_ylabel("R\u00b2")
ax[0].set_ylim(0, max(0.75, cv_df["R2"].max()+0.08)); ax[0].legend()
ax[1].bar(cv_df["Fold"], cv_df["RMSE"], color="#e67e22")
ax[1].set_title("Root Mean Squared Error by Fold"); ax[1].set_ylabel("RMSE (mm)")
plt.tight_layout(); plt.savefig(OUT_FIG/"fig11_cv.png"); plt.close()

# ------------------------------------------------------------------
# Hyperparameter tuning (TimeSeriesSplit)
# ------------------------------------------------------------------
print("Running GridSearchCV ...")
param_grid = {"n_estimators":[50,100],"max_depth":[6,10],"min_samples_split":[2,5]}
grid = GridSearchCV(RandomForestRegressor(random_state=42,n_jobs=-1), param_grid,
                    cv=TimeSeriesSplit(n_splits=3), scoring="neg_root_mean_squared_error", n_jobs=-1)
grid.fit(X_tr, y_tr)
best = grid.best_estimator_
p_best = np.clip(best.predict(X_te),0,None)
best_metrics = reg_metrics(y_te, p_best)
print("Best params:", grid.best_params_, "CV RMSE:", -grid.best_score_)
print("Tuned test metrics:", best_metrics)

# ------------------------------------------------------------------
# Climate anomalies
# ------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(12,4.5))
anom = annual["sum"] - annual["sum"].mean()
colors = ["#c0392b" if v>0 else "#2980b9" for v in anom]
ax.bar(anom.index, anom.values, color=colors, edgecolor="black", lw=.3)
ax.axhline(0,color="black",lw=1)
ax.set_title("Annual Rainfall Anomaly Relative to 42-Year Mean")
ax.set_xlabel("Year"); ax.set_ylabel("Anomaly (mm)")
plt.tight_layout(); plt.savefig(OUT_FIG/"fig12_anomalies.png"); plt.close()

# ------------------------------------------------------------------
# Save all metrics
# ------------------------------------------------------------------
reg_df.to_csv(OUT_REP/"regression_metrics.csv", index=False)
clf_df.to_csv(OUT_REP/"classification_metrics.csv", index=False)
cv_df.to_csv(OUT_REP/"cv_metrics.csv", index=False)
pd.DataFrame(per_class).T.to_csv(OUT_REP/"per_class_rf.csv")

summary = {
    "dataset": stats,
    "regression": reg_df.to_dict(orient="records"),
    "classification": clf_df.to_dict(orient="records"),
    "per_class_rf": per_class,
    "cv": {"folds": cv_df.to_dict(orient="records"),
           "mean_r2": round(float(cv_df.R2.mean()),4),
           "std_r2": round(float(cv_df.R2.std()),4),
           "mean_rmse": round(float(cv_df.RMSE.mean()),3)},
    "tuning": {"best_params": grid.best_params_,
               "cv_rmse": round(float(-grid.best_score_),3),
               "test_metrics": best_metrics},
    "feature_importance": {k: round(float(v),4) for k,v in imp.sort_values(ascending=False).items()},
    "monthly_sum": {m_order[i]: round(float(monthly['sum'].iloc[i]),1) for i in range(12)},
    "annual": {str(k): round(float(v),1) for k,v in annual["sum"].items()},
    "hurdle_prob_weighted": reg_metrics(y_te, p_prob),
}
with open(OUT_REP/"metrics_summary.json","w",encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print("\nDONE. Figures ->", OUT_FIG, "| Data ->", OUT_REP)
