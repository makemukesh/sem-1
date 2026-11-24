"""Fix/upgrade selected report figures + draw architecture, workflow, ER and use-case diagrams."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import seaborn as sns

ROOT = Path(r"D:\sem=1\Project")
OUT = ROOT / "outputs" / "report_figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.labelsize": 10, "axes.grid": True, "grid.alpha": 0.3,
    "figure.dpi": 200, "savefig.dpi": 200, "savefig.bbox": "tight",
})

df = pd.read_excel(ROOT/"data"/"RainVision_Historical_1985_to_Today.xlsx",
                   sheet_name="Rainfall_Data_1985_to_Today")
df["date"] = pd.to_datetime(df["date"])
df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
r = df["rainfall"]

# ---------- FIG 2 : distribution + class bars + monthly ----------
CATEGORIES = ["Dry / Trace","Light","Moderate","Heavy","Torrential"]
counts = df["rainfall_category"].value_counts().reindex(CATEGORIES).fillna(0).astype(int)
fig, ax = plt.subplots(1,3, figsize=(15,4.6))
wet = r[r > 0.05]
ax[0].hist(wet, bins=np.logspace(np.log10(0.06), np.log10(wet.max()), 40), color="#1f77b4")
ax[0].set_xscale("log"); ax[0].set_yscale("log")
ax[0].set_title("Wet-Day Rainfall Distribution (log-log)")
ax[0].set_xlabel("Rainfall (mm)"); ax[0].set_ylabel("Frequency")
colors = ["#95a5a6","#3498db","#f1c40f","#e67e22","#c0392b"]
bars = ax[1].barh(CATEGORIES[::-1], counts.values[::-1], color=colors[::-1])
ax[1].set_title("Rainfall Intensity Class Distribution")
ax[1].set_xlabel("Number of days")
for b,v in zip(bars, counts.values[::-1]):
    ax[1].text(v + max(counts)*0.01, b.get_y()+b.get_height()/2,
               f"{v:,} ({v/len(df)*100:.1f}%)", va="center", fontsize=8)
ax[1].set_xlim(0, max(counts)*1.28)
m_order = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
mmean = df.groupby(df["date"].dt.strftime("%b"))["rainfall"].mean().reindex(m_order)
sns.barplot(x=mmean.index, y=mmean.values, ax=ax[2], palette="Blues_d")
ax[2].set_title("Mean Daily Rainfall by Month"); ax[2].set_xlabel("Month"); ax[2].set_ylabel("Mean Rainfall (mm)")
plt.tight_layout(); plt.savefig(OUT/"fig2_distribution_seasonality.png"); plt.close()

# ---------- FIG 3 : single wide correlation heatmap ----------
fig, ax = plt.subplots(figsize=(8.6,6.4))
cdf = df[["rainfall","temperature","humidity","pressure","wind_speed",
          "previous_rainfall","is_monsoon"]].copy()
cdf.columns = ["Rainfall","Temperature","Humidity","Pressure","Wind Speed","Prev. Rainfall","Monsoon Flag"]
sns.heatmap(cdf.corr(), annot=True, fmt=".2f", cmap="RdBu_r", center=0,
            ax=ax, square=True, cbar_kws={"shrink":.75}, annot_kws={"size":9})
ax.set_title("Correlation Matrix of Meteorological Variables")
plt.tight_layout(); plt.savefig(OUT/"fig3_correlation.png"); plt.close()

# ---------- helper ----------
def box(ax, x, y, w, h, text, fc, ec="#2c3e50", fs=9, bold=False, radius=0.02):
    p = FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle=f"round,pad=0.008,rounding_size={radius}",
                       fc=fc, ec=ec, lw=1.3)
    ax.add_patch(p)
    ax.text(x, y, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", color="#1a1a1a", wrap=True)
    return p

def arrow(ax, x1,y1,x2,y2, color="#34495e", style="-|>", lw=1.6, rad=0.0, ls="-"):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2), arrowstyle=style, mutation_scale=13,
                                 color=color, lw=lw, linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}"))

# ---------- ARCHITECTURE ----------
fig, ax = plt.subplots(figsize=(12,7.2))
ax.set_xlim(0,12); ax.set_ylim(0,10); ax.axis("off"); ax.grid(False)
layers = [
    (8.9, "PRESENTATION LAYER", "#d6eaf8", ["Flask Web UI (HTML5/CSS3/JS)", "Dashboard  |  Prediction Studio", "Model Comparison  |  Dataset Explorer"]),
    (6.7, "SERVICE / API LAYER", "#d5f5e3", ["REST Endpoints (/api/predict, /api/dashboard)", "Input validation & advisory engine"]),
    (4.5, "INTELLIGENCE LAYER", "#fdebd0", ["Regression Suite  |  Classification Suite", "Two-Stage Hurdle Model  |  Ensemble", "Explainable AI (XAI) attribution"]),
    (2.5, "FEATURE & PREPROCESSING LAYER", "#e8daef", ["Cleaning & QA  |  Cyclical encodings", "Lags, rolling windows, pressure tendency"]),
    (0.75, "DATA LAYER", "#f5b7b1", ["Historical dataset (15,279 daily records, 1985-2026)", "Serialized models (.joblib)  |  Reports & figures"]),
]
for y, title, color, items in layers:
    ax.add_patch(FancyBboxPatch((0.4, y-0.9), 11.2, 1.75, boxstyle="round,pad=0.02,rounding_size=0.06",
                                fc=color, ec="#7f8c8d", lw=1.2, alpha=.55))
    ax.text(0.62, y+0.62, title, fontsize=9.5, fontweight="bold", color="#2c3e50")
    ax.text(6.1, y-0.05, "   |   ".join(items), ha="center", va="center", fontsize=9.2)
for y1,y2 in [(1.7,2.5),(3.4,4.5),(5.4,6.7),(7.6,8.9)]:
    arrow(ax, 6, y1-0.75, 6, y2-0.9, style="<|-|>", color="#566573", lw=1.8)
ax.text(6, 9.75, "RainVision System Architecture", ha="center", fontsize=14, fontweight="bold")
plt.tight_layout(); plt.savefig(OUT/"fig_architecture.png"); plt.close()

# ---------- WORKFLOW ----------
fig, ax = plt.subplots(figsize=(12,6.6))
ax.set_xlim(0,12); ax.set_ylim(0,9); ax.axis("off"); ax.grid(False)
steps = [
    (1.5,6.9,"1. Data Acquisition\n(Excel / CSV, 1985-2026)", "#d6eaf8"),
    (4.2,6.9,"2. Data Cleaning &\nPhysical Validation", "#d5f5e3"),
    (6.9,6.9,"3. Exploratory Data\nAnalysis", "#fdebd0"),
    (9.6,6.9,"4. Feature\nEngineering (17 features)", "#e8daef"),
    (9.6,3.9,"5. Chronological Split\n80% Train / 20% Test", "#f5b7b1"),
    (6.9,3.9,"6. Model Training\n(Regression + Classification)", "#f9e79f"),
    (4.2,3.9,"7. Evaluation, CV &\nHyperparameter Tuning", "#d5f5e3"),
    (1.5,3.9,"8. Serialization &\nMetadata Registry", "#d6eaf8"),
    (1.5,0.9,"9. Flask Inference API\n+ Advisories / XAI", "#fdebd0"),
    (6.0,0.9,"10. Dashboard, Prediction\nStudio & Reports", "#e8daef"),
]
w,h = 2.15,1.35
for x,y,t,c in steps:
    box(ax, x,y,w,h,t,c,fs=9)
for (x1,y1),(x2,y2) in [((1.5,6.9),(4.2,6.9)),((4.2,6.9),(6.9,6.9)),((6.9,6.9),(9.6,6.9))]:
    arrow(ax, x1+w/2, y1, x2-w/2, y2)
arrow(ax, 9.6, 6.9-h/2, 9.6, 3.9+h/2)
arrow(ax, 9.6-w/2, 3.9, 6.9+w/2, 3.9)
arrow(ax, 6.9-w/2, 3.9, 4.2+w/2, 3.9)
arrow(ax, 4.2-w/2, 3.9, 1.5+w/2, 3.9)
arrow(ax, 1.5, 3.9-h/2, 1.5, 0.9+h/2)
arrow(ax, 1.5+w/2, 0.9, 6.0-w/2, 0.9)
ax.text(6, 8.55, "RainVision End-to-End Process Workflow", ha="center", fontsize=14, fontweight="bold")
plt.tight_layout(); plt.savefig(OUT/"fig_workflow.png"); plt.close()

# ---------- USE CASE ----------
fig, ax = plt.subplots(figsize=(11,7))
ax.set_xlim(0,12); ax.set_ylim(0,10); ax.axis("off"); ax.grid(False)
ax.add_patch(mpatches.Rectangle((3.1,0.7),6.1,8.4, fill=False, ec="#2c3e50", lw=1.6))
ax.text(6.15, 8.75, "RainVision Platform", ha="center", fontsize=12, fontweight="bold")
uses = [(6.15,7.6,"Upload / Inspect Historical Dataset"),
        (6.15,6.5,"View Climate Dashboard & Analytics"),
        (6.15,5.4,"Select Model (OLS / RF / GB / Hurdle)"),
        (6.15,4.3,"Enter Weather Parameters"),
        (6.15,3.2,"Predict Rainfall Depth & Intensity"),
        (6.15,2.1,"View Advisory & XAI Explanation")]
for x,y,t in uses:
    ax.add_patch(mpatches.Ellipse((x,y), 4.6, 0.72, fc="#d6eaf8", ec="#2c3e50", lw=1.1))
    ax.text(x,y,t,ha="center",va="center",fontsize=8.6)
# actors
for y,name in [(6.9,"Meteorologist /\nDomain Expert"),(2.8,"Citizen /\nDecision Maker")]:
    ax.plot([1.0],[y+0.55],"o",ms=14,mfc="#f5b7b1",mec="#2c3e50")
    ax.plot([1.0,1.0],[y+0.35,y-0.15],color="#2c3e50",lw=1.6)
    ax.plot([0.65,1.35],[y+0.15,y+0.15],color="#2c3e50",lw=1.6)
    ax.plot([1.0,0.72],[y-0.15,y-0.6],color="#2c3e50",lw=1.6)
    ax.plot([1.0,1.28],[y-0.15,y-0.6],color="#2c3e50",lw=1.6)
    ax.text(1.0,y-1.0,name,ha="center",fontsize=8.6)
for vy in [7.6,6.5,5.4,4.3,3.2]:
    ax.plot([1.35,3.85],[6.9,vy],color="#7f8c8d",lw=1.0)
ax.plot([1.35,3.85],[2.8,2.1],color="#7f8c8d",lw=1.0)
ax.plot([1.35,3.85],[2.8,3.2],color="#7f8c8d",lw=1.0)
ax.text(6.15, 9.5, "Use Case Diagram - RainVision", ha="center", fontsize=14, fontweight="bold")
plt.tight_layout(); plt.savefig(OUT/"fig_usecase.png"); plt.close()

# ---------- LOGICAL DATA MODEL (ER) ----------
fig, ax = plt.subplots(figsize=(11,6.2))
ax.set_xlim(0,12); ax.set_ylim(0,8); ax.axis("off"); ax.grid(False)
def entity(x,y,title,fields,w=2.6):
    hh = 0.42 + 0.3*len(fields)
    ax.add_patch(mpatches.Rectangle((x-w/2,y-hh/2),w,hh, fc="white", ec="#2c3e50", lw=1.4))
    ax.add_patch(mpatches.Rectangle((x-w/2,y+hh/2-0.42),w,0.42, fc="#2c3e50", ec="#2c3e50"))
    ax.text(x,y+hh/2-0.21,title,ha="center",va="center",color="white",fontsize=9,fontweight="bold")
    for i,f in enumerate(fields):
        ax.text(x-w/2+0.12, y+hh/2-0.42-0.15-0.3*i, f, fontsize=7.6, va="center")
    return (x,y,hh,w)
e1 = entity(2.2,5.0,"OBSERVATION",["PK observation_id","date (DATE)","location (VARCHAR)","temperature (FLOAT)","humidity (FLOAT)","pressure (FLOAT)","wind_speed (FLOAT)","rainfall (FLOAT)"])
e2 = entity(6.0,5.2,"FEATURE_VECTOR",["PK feature_id","FK observation_id","rain_lag_1..3 (FLOAT)","roll_mean/sum/max (FLOAT)","sin/cos_day_of_year","is_monsoon (INT)"], w=3.0)
e3 = entity(9.9,5.2,"PREDICTION",["PK prediction_id","FK feature_id","model_name (VARCHAR)","predicted_mm (FLOAT)","intensity_class (VARCHAR)","advisory (TEXT)","created_at (TIMESTAMP)"], w=3.2)
e4 = entity(2.2,1.6,"MODEL_REGISTRY",["PK model_id","model_name (VARCHAR)","algorithm (VARCHAR)","r2_score (FLOAT)","mae_mm (FLOAT)","artifact_path (VARCHAR)","trained_at (TIMESTAMP)"], w=3.0)
e5 = entity(7.2,1.5,"CLIMATE_SUMMARY",["PK summary_id","year (INT)","total_rainfall_mm","rainy_days (INT)","avg_temp_c (FLOAT)"], w=2.8)
arrow(ax,3.5,5.0,4.5,5.05, style="-", lw=1.2); ax.text(4.0,5.35,"1 : 1",fontsize=7.5)
arrow(ax,7.5,5.2,8.3,5.2, style="-", lw=1.2); ax.text(7.9,5.55,"1 : N",fontsize=7.5)
arrow(ax,2.2,3.6,2.2,2.7, style="-", lw=1.2); ax.text(2.4,3.15,"learns from",fontsize=7.5)
ax.text(6,7.6,"Logical Data Model (Entity-Relationship Diagram)",ha="center",fontsize=13,fontweight="bold")
plt.tight_layout(); plt.savefig(OUT/"fig_erd.png"); plt.close()

print("diagrams done")
