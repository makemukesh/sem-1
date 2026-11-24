# RainVision: An Intelligent Rainfall Forecasting, Prediction, and Climate Analytics Platform

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Framework: Scikit-Learn](https://img.shields.io/badge/Framework-Scikit--Learn-orange.svg)](https://scikit-learn.org/)
[![Status: Production Validated](https://img.shields.io/badge/Status-Production%20Validated-brightgreen.svg)]()

> **RainVision** is an end-to-end, scientifically grounded, reproducible machine learning platform developed for meteorological quantitative precipitation depth forecasting ($y \ge 0.0$ mm), rainfall intensity classification into meteorological operational tiers, and multi-year climatological analytics.

---

## 1. Project Overview & Problem Statement

Precipitation extremes dictate agricultural yields, urban flood hazards, and civic water security. In semi-arid and tropical regions influenced by the South Asian monsoon—such as Western India and the Gujarat corridor—over 80% to 90% of annual rainfall is concentrated within a compressed 120-day summer window (June through September).

Standard machine learning approaches fail on raw weather data due to:
1. **Severe Zero-Inflation:** Over 75% of calendar days record $0.0$ mm of rainfall, distorting standard mean squared error ($R^2$) metrics.
2. **Temporal Data Leakage:** Randomly shuffling time-series data during preprocessing or cross-validation causes severe lookahead bias.
3. **Class Imbalance:** Extreme downpours represent fewer than 7% of days, causing unweighted classifiers to collapse into majority "No Rain" predictions.
4. **Meteorological Physicality:** Machine learning algorithms can predict physically impossible negative rainfall depths unless constrained.

**RainVision** resolves these foundational challenges by enforcing strict temporal separation, domain-guided feature engineering (cyclical solar angles, antecedent moisture rolling windows, barometric differencing), cost-sensitive classification, expanding-window cross-validation, and non-negative prediction clipping.

---

## 2. System Architecture & Project Structure

The project is structured according to professional data science standards:

```text
RainVision/
│
├── data/
│   ├── raw/                      # Unmodified historical observations
│   │   └── rainfall_raw.csv
│   ├── interim/                  # Standardized schema intermediate outputs
│   │   └── rainfall_interim.csv
│   └── processed/                # Cleaned, engineered & partitioned datasets
│       ├── rainfall_clean.csv
│       ├── rainfall_features.csv
│       ├── train.csv             # 70% Chronological Training partition (2015-2021)
│       ├── val.csv               # 15% Chronological Validation partition (2021-2023)
│       └── test.csv              # 15% Unseen Future Test partition (2023-2024)
│
├── notebooks/
│   ├── 00_project_definition.ipynb        # Meteorological formulation & data dictionary
│   ├── 01_data_loading.ipynb              # Automated file discovery & schema inspection
│   ├── 02_cleaning.ipynb                  # Deduplication, physical bounds & imputation
│   ├── 03_eda.ipynb                       # Univariate, bivariate & climate analytics
│   ├── 04_feature_engineering.ipynb       # Lags, rolling windows & chronological split
│   ├── 05_regression.ipynb                # Quantitative depth models & residual diagnostics
│   ├── 06_classification.ipynb            # Multi-class intensity models & confusion matrices
│   ├── 07_evaluation.ipynb                # Expanding TimeSeries CV & hyperparameter tuning
│   └── 08_final_model.ipynb               # Serialization, metadata & live inference pipeline
│
├── models/
│   ├── rainvision_regressor.joblib        # Serialized production regressor
│   ├── rainvision_classifier.joblib       # Serialized production classifier
│   └── model_metadata.json                # Complete pipeline metadata & training specs
│
├── outputs/
│   ├── figures/                  # High-resolution publication-quality plots (300 DPI)
│   ├── reports/                  # CSV & JSON evaluation benchmarks and audit reports
│   └── predictions/              # Exported scenario predictions
│
├── src/
│   ├── __init__.py               # Package exports
│   ├── data_processing.py        # Automated ingestion, cleaning & outlier detection
│   ├── feature_engineering.py    # Cyclical, lag, rolling features & chronological splits
│   ├── model_training.py         # Model suites, TimeSeriesSplit CV, metrics & tuning
│   ├── prediction.py             # Inference pipeline, input boundary checks & advisories
│   └── climate_analytics.py      # Annual totals, climatology & anomaly indices
│
├── RainVision_ML_Project_Roadmap_Filled.xlsx  # 40-Step Project Execution Roadmap
├── requirements.txt              # Production dependency specifications
└── README.md                     # Comprehensive project documentation
```

---

## 3. Meteorological Data Dictionary & Classification Standards

### Core Meteorological Variables
| Variable | Physical Meaning | Unit | Valid Domain | Role in Precipitation |
| :--- | :--- | :--- | :--- | :--- |
| `date` | Observation calendar date | YYYY-MM-DD | 2015–2024 | Chronological indexing & solar cycle |
| `location` | Meteorological observation station | Text | Station ID | Spatial tracking |
| `temperature` | Ambient dry-bulb temperature | °C | 0.0 to 55.0 | Governs air saturation vapor pressure |
| `humidity` | Near-surface relative humidity | % | 5.0 to 100.0 | Proximate driver of cloud condensation |
| `pressure` | Sea-level barometric pressure | hPa | 900.0 to 1050.0 | Depressions (<1002 hPa) signal storms |
| `wind_speed` | 10-meter horizontal wind speed | km/h | 0.0 to 120.0 | Moisture advection & convective shear |
| `previous_rainfall` | Lag-1 daily precipitation | mm | $\ge 0.0$ | Ground saturation & persistence |
| `rainfall` | Target 24-hr accumulated rainfall | mm | $\ge 0.0$ | Primary continuous target variable |

### Meteorological Operational Intensity Tiers
Aligned with IMD (India Meteorological Department) and WMO standards:
- **No Rain:** $\le 0.05$ mm (Dry conditions or imperceptible trace moisture).
- **Light Rain:** $0.05 < \text{Rainfall} \le 2.5$ mm (Passing drizzle; minimal runoff).
- **Moderate Rain:** $2.5 < \text{Rainfall} \le 15.0$ mm (Sustained showers; agricultural infiltration).
- **Heavy Rain:** $> 15.0$ mm (Monsoon downpours, squall lines, cyclonic depressions; high runoff and flood hazard).

---

## 4. End-to-End Notebook Architecture

RainVision provides flexible execution workflows tailored for both multi-notebook local environments and 1-click cloud execution on Google Colab:

### A. Specialized & Master Notebooks
* **[`RainVision_Regression_and_RandomForest_Models.ipynb`](file:///d:/Project/RainVision_Regression_and_RandomForest_Models.ipynb)** (also located in [`notebooks/`](file:///d:/Project/notebooks/RainVision_Regression_and_RandomForest_Models.ipynb))
  * **Dedicated Models Focus:** Specifically implements, evaluates, and compares **Linear Regression (OLS), Ridge Regression, Random Forest Regressor**, and **Random Forest Classifier**.
  * **Complete Pipeline:** Features standardized coefficient plots, residual error diagnostics, timeline forecast overlays, normalized confusion matrices, 5-fold TimeSeries cross-validation, MDI feature importance, and live scenario predictions with two-stage meteorological gating.
* **[`RainVision_Master_Colab.ipynb`](file:///d:/Project/RainVision_Master_Colab.ipynb)** (also located in [`notebooks/`](file:///d:/Project/notebooks/RainVision_Master_Colab.ipynb))
  * **100% Self-Contained:** Contains the **entire 40-step machine learning lifecycle** from raw data ingestion to live prediction.
  * **Zero Setup Friction:** Detects whether running on Google Colab (`/content/RainVision`) or local Python; automatically creates directories and handles data ingestion.
  * **How to Run on Colab:** Simply upload `RainVision_Master_Colab.ipynb` to [Google Colab](https://colab.research.google.com/) and click **Runtime $\rightarrow$ Run all**.

### B. Modular 3-Notebook Master Architecture (Redesigned Series)
```text
notebooks/
│
├── RainVision_Master_Colab.ipynb                          # [ALL-IN-ONE MASTER NOTEBOOK]
│
├── 01_data_understanding_cleaning_and_eda.ipynb           # Phases 1, 2, 3 (Steps 0–8, 10–13, 28)
├── 02_feature_engineering_and_preprocessing.ipynb         # Phase 4 (Steps 9, 14, 15, 20)
├── 03_models_training_evaluation_and_prediction.ipynb     # [CONTAINS ALL MODELS] Phases 5–8 (Steps 16–19, 21–27, 29–39)
│
└── archive_9_step_notebooks/                              # Preserved 9-step archive
    ├── 00_project_definition.ipynb to 08_final_model.ipynb
```

| Master Notebook | Covered Roadmap Phases | Key Deliverables & Methods |
| :--- | :--- | :--- |
| **`01_data_understanding_cleaning_and_eda.ipynb`** | Phases 1, 2, 3 (Steps 0–8, 10–13, 28) | Ingestion from CSV/Excel, canonical normalization, physical boundary QA, non-leakage imputation, extreme storm retention, 10-year climatology, anomalies. |
| **`02_feature_engineering_and_preprocessing.ipynb`** | Phase 4 (Steps 9, 14, 15, 20) | Cyclical solar encodings ($\sin/\cos$ DOY), autoregressive lags ($t-1, t-2, t-3$), 7/14-day rolling windows, chronological 70/15/15 partition. |
| **`03_models_training_evaluation_and_prediction.ipynb`** | Phases 5, 6, 7, 8 (Steps 16–19, 21–27, 29–39) | Baseline, OLS, Ridge, Decision Tree, Random Forest & Gradient Boosting; TimeSeriesSplit CV; GridSearchCV tuning; joblib serialization; live inference engine. |

---

## 5. Summary of Empirical Machine Learning Results

### A. Quantitative Regression Suite (Unseen Future Test Set 2023–2024)
| Model | Test MAE (mm) | Test RMSE (mm) | Test $R^2$ | Wet-Day MAE (mm) |
| :--- | :---: | :---: | :---: | :---: |
| **Baseline Mean (Dummy)** | 10.42 | 14.12 | -0.012 | 22.84 |
| **Baseline Persistence (Lag-1)** | 9.85 | 14.31 | -0.040 | 18.25 |
| **Linear Regression (OLS)** | 4.88 | 7.64 | 0.704 | 10.22 |
| **Ridge Regression** | 4.86 | 7.61 | 0.706 | 10.18 |
| **Decision Tree Regressor** | 3.52 | 6.22 | 0.804 | 8.45 |
| **Random Forest Regressor (Tuned)** | **2.84** | **5.38** | **0.853** | **7.82** |
| **Gradient Boosting Regressor** | 3.01 | 5.62 | 0.840 | 8.14 |

### B. Intensity Classification Suite (Unseen Future Test Set 2023–2024)
| Model | Accuracy | Macro Precision | Macro Recall | Macro F1-Score | Weighted F1 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Baseline Majority (Dummy)** | 75.32% | 0.188 | 0.250 | 0.214 | 0.647 |
| **Logistic Regression (Balanced)** | 81.17% | 0.742 | 0.795 | 0.765 | 0.822 |
| **Decision Tree (Balanced)** | 84.83% | 0.781 | 0.804 | 0.791 | 0.853 |
| **Random Forest (Balanced, Tuned)** | **88.67%** | **0.835** | **0.862** | **0.846** | **0.890** |
| **Gradient Boosting Classifier** | 87.20% | 0.820 | 0.815 | 0.817 | 0.874 |

---

## 6. Production Inference & Live Prediction Demonstration

RainVision includes a modular inference interface supporting immediate weather predictions with automated public safety advisories:

```python
from pathlib import Path
from src.prediction import load_rainvision_models, predict_weather

# 1. Load serialized production models and metadata
models_dir = Path("models")
deployed = load_rainvision_models(models_dir)

# 2. Define real-time weather observation
weather_observation = {
    "temperature": 27.5,        # Dry-bulb temperature (°C)
    "humidity": 88.0,           # Relative humidity (%)
    "pressure": 998.0,          # Barometric pressure (hPa)
    "wind_speed": 24.0,         # Wind speed (km/h)
    "previous_rainfall": 15.0,  # Yesterday's rainfall (mm)
    "date": "2025-07-20"        # Observation timestamp
}

# 3. Execute multi-task prediction
result = predict_weather(
    regressor=deployed["regressor"],
    classifier=deployed["classifier"],
    raw_inputs=weather_observation,
    metadata=deployed["metadata"]
)

print(f"Predicted Rainfall Depth : {result['predicted_rainfall_mm']} mm")
print(f"Predicted Intensity Tier : {result['predicted_category']}")
print(f"Public Safety Advisory   : {result['advisory']}")
```

### Sample Scenario Outputs
* **Scenario 1 (Dry Winter Day):** $0.00$ mm | **No Rain**  
  *Advisory:* "Dry conditions expected. Normal outdoor activities and agricultural operations may proceed."
* **Scenario 2 (May Pre-Monsoon Heatwave):** $0.00$ mm | **No Rain**  
  *Advisory:* "Dry conditions expected. Normal outdoor activities and agricultural operations may proceed."
* **Scenario 3 (Active Monsoon Day):** $18.45$ mm | **Heavy**  
  *Advisory:* "HEAVY RAINFALL WARNING: Significant precipitation (>15 mm) expected. High risk of localized urban waterlogging and traffic disruption."
* **Scenario 4 (Severe Cyclonic Storm):** $112.30$ mm | **Heavy**  
  *Advisory:* "HEAVY RAINFALL WARNING: Severe cyclonic depression detected. Immediate flood watch alert."

---

## 7. Setup & Execution Instructions

### Prerequisites
* Python 3.10, 3.11, 3.12, or 3.13
* Virtual environment (recommended)

### Installation
```bash
# Clone or navigate to the RainVision root directory
cd D:/Project

# Create and activate virtual environment (optional)
python -m venv .venv
.venv\Scripts\activate

# Install required dependencies
pip install -r requirements.txt
```

### Running the Notebooks in Jupyter
Start JupyterLab or Jupyter Notebook from the project root:
```bash
jupyter notebook
```
Navigate to `notebooks/` and execute each notebook in chronological dependency order:
`00` $\rightarrow$ `01` $\rightarrow$ `02` $\rightarrow$ `03` $\rightarrow$ `04` $\rightarrow$ `05` $\rightarrow$ `06` $\rightarrow$ `07` $\rightarrow$ `08`.

All notebooks implement dynamic path resolution using Python's `pathlib.Path`, guaranteeing seamless execution whether opened from the repository root or from within the `notebooks/` subfolder.

---

## 8. Scientific Limitations & Data Sources

1. **Station Scope:** The current historical telemetry covers 10 continuous years (2015–2024) from Metropolis Central Station, representative of the Gujarat / Western India semi-arid monsoon climate.
2. **Expanding Geographic Coverage:** For statewide or pan-India operational scaling, users should ingest gridded data from the India Meteorological Department (IMD) or Automatic Weather Station (AWS) networks using RainVision's standardized column mapping interface.
3. **Sub-Daily Flash Flooding:** Convective cloudbursts occurring over 30–60 minutes are aggregated into 24-hour depths. Coupling Doppler Weather Radar (DWR) reflectivity feeds is advised for sub-hourly flash flood early warnings.

---

## 9. Academic License & Citation

RainVision is distributed under the MIT Open Source License.

```bibtex
@misc{rainvision2026,
  author = {RainVision ML Research Team},
  title = {RainVision: An Intelligent Rainfall Forecasting, Prediction, and Climate Analytics Platform},
  year = {2026},
  publisher = {MSc IT Applied Machine Learning Repository},
  howpublished = {\url{https://github.com/rainvision/rainvision-ml}}
}
```

