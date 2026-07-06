# 🏎️ F1 Race Predictor

[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen.svg)](https://f1-race-predictor-yr49.onrender.com)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat&logo=scikit-learn&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

**[🏁 Try the live demo](https://f1-race-predictor-yr49.onrender.com)**

A machine-learning model that predicts Formula 1 finishing order, wrapped in an
interactive F1-broadcast-style interface. Pick a circuit, simulate a qualifying
order, and watch a model trained on **2014–2026 race data** rank the grid with
calibrated win and podium probabilities.

This is a passion project — I'm an F1 fan who wanted to find out how much of a
race is actually predictable. The honest answer: a lot of it is qualifying, the
rest is car and driver form, and F1 still keeps ~45% of winners genuinely up for
grabs. The numbers below are all from a real backtest, not round-number marketing.

<div align="center">

![F1 Predictor Demo](docs/images/f1-predictor-demo.gif)

</div>

---

## 📊 What it actually does

Given a qualifying order and a circuit, the system predicts the full finishing
order plus each driver's probability of **winning** and reaching the **podium**.

- **Data** — official results & qualifying for every race **2014–2026**
  (259 races, 5,259 driver-race rows) from the **Jolpica / Ergast F1 API**, the
  maintained successor to Ergast. The 2026 season is pulled live, so the grid
  reflects the real field — Cadillac and Audi on it, Hamilton at Ferrari.
- **Model** — scikit-learn **HistGradientBoosting**: a finishing-position
  regressor for the running order, plus calibrated win / podium classifiers for
  the probabilities.
- **Features** — all known *before* lights out, so there's no leakage:
  qualifying & grid slot, rolling driver form (last 3/5 races), DNF rate,
  season-to-date points, constructor form, the driver's history at that circuit,
  and the intra-team qualifying gap.

## 🎯 Does it work? (honest backtest)

Validation is a **time-series backtest** — for each held-out season the model is
trained only on *earlier* seasons, then scored on every race. Pooled over
**2022–2025 (92 races)**, against the natural baseline of "the grid order is the
result":

| Metric | Model | Grid baseline |
|---|:---:|:---:|
| Winner — top-1 accuracy | **54.3%** | 50.0% |
| Podium — precision@3 | **65.2%** | 64.5% |
| Finishing order — mean Spearman ρ | **0.647** | 0.607 |

Pole position is a famously strong predictor in F1, so the grid baseline is hard
to beat — but the model edges it on the winner call and clearly improves the
full-grid ordering, while adding calibrated probabilities the naive baseline
can't give you.

### What drives a prediction
Permutation importance on the 2025 hold-out, grouped:

| Signal group | Importance |
|---|:---:|
| Qualifying & grid | 39% |
| Car / constructor form | 27% |
| Driver recent form | 21% |
| Experience & teammate gap | 9% |
| Circuit history | 4% |

Qualifying dominates, but car and driver form together matter just as much —
which is why a clean qualifying lap doesn't guarantee the win.

## 🚀 Quick start

**Try it online:** [f1-race-predictor-yr49.onrender.com](https://f1-race-predictor-yr49.onrender.com)

**Run locally:**
```bash
pip install -r requirements.txt
python app.py            # -> http://localhost:5000
```
The repo ships with the trained model, so the app runs immediately.

**Reproduce the model from scratch:**
```bash
pip install pandas pyarrow scikit-learn scipy requests
python data/ingest.py    # pull 2014-2026 results from Jolpica -> data/f1_results.parquet
python model/train.py    # feature-engineer, backtest, and write model/ artifacts
```
`data/ingest.py` caches every API response under `data/_cache/`, so re-runs are
instant and stay well within the API's rate limits.

## 🧱 How it's built

```
data/ingest.py            # Jolpica/Ergast -> tidy parquet (cached, rate-limited)
model/train.py            # leakage-safe features, time-series backtest, artifacts
model/predict.py          # inference for the app (numpy only, no pandas at serve)
model/f1_model.pkl        # trained regressor + win/podium classifiers
model/driver_form_2026.json  # current-season form snapshot the app predicts from
model/metrics.json        # the backtest numbers quoted above
app.py                    # Flask app + F1-themed UI
```

The interface keeps two genuinely meaningful controls:
- **Circuit selector** — feeds each driver's real historical average finish at
  that track into the model.
- **Qualifying-influence slider** — blends the raw grid order with the model's
  form-aware prediction (100% = trust qualifying, 0% = trust the model).

## 🛠️ Built with

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat&logo=scikit-learn&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?style=flat&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat&logo=numpy&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)
![Render](https://img.shields.io/badge/Render-46E3B7?style=flat&logo=render&logoColor=white)

## 🔮 Possible next steps

- FastF1 weather/telemetry enrichment (the model currently has no weather input — wet-weather upsets are part of the unexplained variance)
- Learning-to-rank objective instead of position regression
- Bayesian intervals on the probabilities
- Auto-retrain after each race weekend via a scheduled job

## 🙏 Data & credits

- **[Jolpica / Ergast F1 API](https://github.com/jolpica/jolpica-f1)** — race results, qualifying, and standings (the maintained Ergast successor)
- **[scikit-learn](https://scikit-learn.org/)** — gradient-boosting models and validation
- **[Flask](https://flask.palletsprojects.com/)** — web framework

*Built because I love F1 and wanted to know how predictable it really is.*

---
MIT License
