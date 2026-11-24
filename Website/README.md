# 🌧️ RainVision — Intelligent Rainfall Prediction & Climate Analytics

RainVision is an end-to-end meteorological machine learning web platform built strictly with **HTML5, CSS3, Vanilla JavaScript, Python, Flask, Pandas, NumPy, Scikit-learn, Joblib, and Chart.js**.

It connects directly with trained Scikit-learn models, including a Random Forest, Gradient Boosting, a two-stage rainfall hurdle model, linear regression, and a validated Random Forest/Gradient Boosting blended ensemble. The API calculates metrics against the workbook's held-out period rather than presenting hard-coded scores.

---

## 🚀 Quick Start: How to Run the Website

### Step 1: Open Terminal in the Website Directory
```powershell
cd "d:\sem=1\website"
```

### Step 2: Install Python Dependencies (If not already installed)
```powershell
pip install -r requirements.txt
```

### Step 3: Start the Flask Application
```powershell
python app.py
```

### Step 4: Open in Web Browser
Open your browser and navigate to:
```
http://localhost:5000
```
or
```
http://127.0.0.1:5000
```

---

## 🧪 Running Automated Tests

Run the built-in unit and integration test suite:
```powershell
python tests/test_prediction.py
```

Train the website model artifacts and publish them to both `Project/models/` and `Website/models/`:
```powershell
cd ..\Project
python scripts\train_website_models.py
```

The script reserves `Heldout_Test_Data` for evaluation and includes the validated ensemble artifact from `Project/models/redesigned_v2/`.

---

## 📁 Project Architecture

```
d:\sem=1\website\
├── app.py                     # Flask server and REST API controller
├── requirements.txt           # Python dependencies
├── .env.example               # Configuration example
├── README.md                  # Project documentation
├── data/
│   └── RainVision_Historical_1985_to_Today.xlsx
├── models/
│   ├── ensemble_model.joblib        # Default validated blended ensemble
│   ├── regression_model.joblib
│   ├── random_forest_model.joblib
│   ├── gradient_boosting_model.joblib
│   ├── hurdle_model.joblib
│   └── model_metadata.json          # Training run and held-out metrics
├── ml/
│   ├── ensemble.py            # Serialized ensemble inference wrapper
│   ├── preprocessing.py       # Physical boundary validation & 17-feature constructor
│   ├── prediction.py          # Real-time inference engine and advisory generator
│   └── evaluation.py          # Empirical metrics evaluation on workbook holdout
├── static/
│   ├── css/
│   │   └── style.css          # Pure CSS3 styling (Deep navy, cyan, responsive)
│   └── js/
│       └── script.js          # Modular Vanilla JS controller & Chart.js renderer
├── templates/
│   └── index.html             # Semantic HTML5 single-page application
└── tests/
    └── test_prediction.py     # Website and ML integration tests
```

---

## 🌐 Features & Pages

- **Home Page**: Hero section, core platform architecture, and quick access.
- **Meteorological Dashboard**: 6 dynamic KPI cards and 4 interactive Chart.js visualizations (30-day trends, frequency distribution bins, monthly monsoon profile, 10-year totals).
- **Rainfall Prediction Studio**: Select a trained model, input weather variables or use presets (Monsoon, Sunny, Pre-Monsoon, Winter), and view predictions with intensity gauge and severity advisory.
- **Model Comparison**: Compare model predictions and holdout evaluation metrics ($R^2$, MAE, RMSE, MSE).
- **Dataset Explorer**: Searchable, sortable, paginated table of 15,279 historical daily observations with custom CSV validation tool.
- **Historical Analytics**: 10-year annual precipitation pattern and climate analysis.
- **About Project**: Capstone academic documentation, dataset parameters, and leak-free lag preprocessing workflow.
