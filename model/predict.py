#!/usr/bin/env python3
"""
Inference for the live app.

Loads the trained models + the 2026 current-form snapshot once, then turns a
qualifying order (a list of driver codes, P1..Pn) plus a chosen circuit into a
real predicted finishing order with calibrated win/podium probabilities.

No pandas/pyarrow at serve time — only numpy + the pickled sklearn models — so
the deployment stays light.
"""
from __future__ import annotations

import json
import warnings
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

# We intentionally serve with plain numpy arrays (no pandas at runtime); silence
# the resulting "X does not have valid feature names" sklearn notice.
warnings.filterwarnings("ignore", message="X does not have valid feature names")

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "model" / "f1_model.pkl"
FORM_PATH = ROOT / "model" / "driver_form_2026.json"


@lru_cache(maxsize=1)
def _load():
    bundle = joblib.load(MODEL_PATH)
    form = json.loads(FORM_PATH.read_text())
    return bundle, form


def available():
    """Driver snapshot + circuit list for building the UI."""
    _, form = _load()
    return form


def _row(code: str, grid_pos: int, circuit_id: str, teammate_pos: int | None,
         form: dict, features: list[str]) -> list[float]:
    d = form["drivers"][code]
    teammate_gap = np.nan
    if teammate_pos is not None:
        teammate_gap = 0.0 if grid_pos < teammate_pos else 0.2   # out-qualified -> small penalty
    values = {
        "grid": float(grid_pos),
        "quali_pos": float(grid_pos),
        "quali_gap": np.nan,                       # no simulated lap times -> let HGB handle
        "drv_form3": d.get("drv_form3"),
        "drv_form5": d.get("drv_form5"),
        "drv_dnf5": d.get("drv_dnf5"),
        "drv_pts_season": d.get("drv_pts_season"),
        "drv_races_prior": d.get("drv_races_prior"),
        "drv_circuit_hist": d.get("circuit_hist", {}).get(circuit_id, np.nan),
        "con_form5": d.get("con_form5"),
        "con_dnf5": d.get("con_dnf5"),
        "con_pts_season": d.get("con_pts_season"),
        "teammate_quali_gap": teammate_gap,
    }
    return [np.nan if values[f] is None else float(values[f]) for f in features]


def predict_race(grid_order: list[str], circuit_id: str,
                 quali_influence: float = 0.7) -> dict:
    """grid_order: driver codes in qualifying order (index 0 == pole)."""
    bundle, form = _load()
    feats = bundle["features"]
    pos = {c: i + 1 for i, c in enumerate(grid_order)}
    team_of = {c: form["drivers"][c]["constructor_id"]
               for c in grid_order if c in form["drivers"]}

    rows, codes = [], []
    for i, code in enumerate(grid_order):
        if code not in form["drivers"]:
            continue
        mate = next((c for c in grid_order
                     if c != code and team_of.get(c) == team_of.get(code)), None)
        rows.append(_row(code, i + 1, circuit_id, pos.get(mate), form, feats))
        codes.append(code)

    if not rows:
        return {"predictions": [], "podium_confidence": 0.0, "reshuffle": 0.0}

    X = np.array(rows, dtype=float)
    pred_pos = bundle["regressor"].predict(X)
    p_win = bundle["win_clf"].predict_proba(X)[:, 1]
    p_pod = bundle["podium_clf"].predict_proba(X)[:, 1]

    # blend the model's form-aware order with the raw grid order
    grid_rank = np.array([pos[c] for c in codes], dtype=float)
    model_rank = pred_pos.argsort().argsort() + 1.0
    blended = quali_influence * grid_rank + (1 - quali_influence) * model_rank
    order = np.argsort(blended, kind="stable")

    predictions = []
    for final_pos, idx in enumerate(order, start=1):
        code = codes[idx]
        d = form["drivers"][code]
        predictions.append({
            "position": final_pos,
            "code": code,
            "name": d["driver_name"],
            "team": d["constructor_name"],
            "number": d["car_number"],
            "qualifying": pos[code],
            "change": final_pos - pos[code],
            "p_win": round(float(p_win[idx]), 3),
            "confidence": round(float(p_pod[idx]), 3),   # podium probability
        })

    podium_conf = float(np.mean([p["confidence"] for p in predictions[:3]])) if predictions else 0.0
    reshuffle = float(np.mean([abs(p["change"]) for p in predictions])) if predictions else 0.0
    return {
        "predictions": predictions,
        "podium_confidence": round(podium_conf, 3),
        "reshuffle": round(reshuffle, 1),
    }
