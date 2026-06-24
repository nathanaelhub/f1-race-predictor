#!/usr/bin/env python3
"""
Train the F1 finishing-order model.

Targets two things from features known BEFORE lights-out (no leakage):
  - finish position  (HistGradientBoostingRegressor)  -> rank drivers in a race
  - podium (top-3)   (HistGradientBoostingClassifier)  -> calibrated confidence

Validation is a proper time-series backtest: for each held-out season we train
only on earlier seasons, predict every race, and score:
  - winner top-1 accuracy   (did our predicted P1 actually win?)
  - podium precision@3      (how many of our top-3 finished top-3?)
  - mean per-race Spearman  (rank correlation of predicted vs actual order)
All compared against the natural baseline of "finish == grid".

Outputs (model/):
  - f1_model.pkl            final regressor + podium classifier + metadata
  - metrics.json            backtest numbers used in the README/portfolio
  - driver_form_2026.json   per-driver current-form snapshot for the live app
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "f1_results.parquet"
OUT = ROOT / "model"

FEATURES = [
    "grid", "quali_pos", "quali_gap",
    "drv_form3", "drv_form5", "drv_dnf5", "drv_pts_season", "drv_races_prior",
    "drv_circuit_hist",
    "con_form5", "con_dnf5", "con_pts_season",
    "teammate_quali_gap",
]


# ----------------------------------------------------------------------------- features
def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Leakage-safe features: every aggregate uses only earlier races."""
    df = df.sort_values(["date", "round", "finish_pos"]).reset_index(drop=True)

    # qualifying gap to pole within each race (seconds)
    pole = df.groupby(["season", "round"])["quali_best_s"].transform("min")
    df["quali_gap"] = df["quali_best_s"] - pole

    # ---- per-driver rolling form (shifted so the current race is excluded) ----
    g = df.groupby("driver_id", group_keys=False)
    df["drv_form3"] = g["finish_pos"].apply(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
    df["drv_form5"] = g["finish_pos"].apply(lambda s: s.shift(1).rolling(5, min_periods=1).mean())
    df["drv_dnf5"] = g["finished"].apply(
        lambda s: (~s).shift(1).rolling(5, min_periods=1).mean())
    df["drv_races_prior"] = g.cumcount()

    # season-to-date points before this race
    df["drv_pts_season"] = (
        df.groupby(["season", "driver_id"])["points"]
        .apply(lambda s: s.shift(1).cumsum()).reset_index(level=[0, 1], drop=True)
    )

    # driver history at this circuit (expanding mean finish, shifted)
    df["drv_circuit_hist"] = (
        df.groupby(["driver_id", "circuit_id"])["finish_pos"]
        .apply(lambda s: s.shift(1).expanding().mean()).reset_index(level=[0, 1], drop=True)
    )

    # ---- per-constructor rolling form ----
    gc = df.groupby("constructor_id", group_keys=False)
    df["con_form5"] = gc["finish_pos"].apply(lambda s: s.shift(1).rolling(10, min_periods=1).mean())
    df["con_dnf5"] = gc["finished"].apply(lambda s: (~s).shift(1).rolling(10, min_periods=1).mean())
    df["con_pts_season"] = (
        df.groupby(["season", "constructor_id"])["points"]
        .apply(lambda s: s.shift(1).cumsum()).reset_index(level=[0, 1], drop=True)
    )

    # teammate qualifying gap (this driver's quali time minus team's best that race)
    team_best = df.groupby(["season", "round", "constructor_id"])["quali_best_s"].transform("min")
    df["teammate_quali_gap"] = df["quali_best_s"] - team_best

    df["podium"] = (df["finish_pos"] <= 3).astype(int)
    df["win"] = (df["finish_pos"] == 1).astype(int)
    return df


# ----------------------------------------------------------------------------- scoring
def race_metrics(grp: pd.DataFrame, rank_col: str, win_col: str, podium_col: str,
                 ascending: bool = True) -> dict:
    """Score one race. rank_col drives the full order (Spearman); win_col and
    podium_col (probabilities, higher=better) drive the top-end calls."""
    actual_winner = grp.loc[grp["finish_pos"] == 1, "driver_id"]
    actual_podium = set(grp.loc[grp["finish_pos"] <= 3, "driver_id"])
    pred_winner = grp.sort_values(win_col, ascending=False)["driver_id"].iloc[0]
    pred_podium = set(grp.sort_values(podium_col, ascending=False)["driver_id"].head(3))
    rho = spearmanr(grp[rank_col] * (1 if ascending else -1), grp["finish_pos"]).correlation
    return {
        "winner_hit": int(len(actual_winner) and pred_winner == actual_winner.iloc[0]),
        "podium_p3": len(pred_podium & actual_podium) / 3.0,
        "spearman": rho if rho == rho else 0.0,   # guard NaN
    }


def _fit_fold(train: pd.DataFrame):
    reg = HistGradientBoostingRegressor(
        max_depth=4, learning_rate=0.06, max_iter=400, l2_regularization=1.0, random_state=42)
    reg.fit(train[FEATURES], train["finish_pos"])
    win = HistGradientBoostingClassifier(
        max_depth=4, learning_rate=0.06, max_iter=400, l2_regularization=1.0, random_state=42)
    win.fit(train[FEATURES], train["win"])
    pod = HistGradientBoostingClassifier(
        max_depth=4, learning_rate=0.06, max_iter=400, l2_regularization=1.0, random_state=42)
    pod.fit(train[FEATURES], train["podium"])
    return reg, win, pod


def evaluate(df: pd.DataFrame, test_seasons: list[int]) -> dict:
    """Time-series backtest: train on earlier seasons, score each held-out one."""
    per_season = {}
    pooled_model, pooled_grid = [], []
    for ts in test_seasons:
        train = df[df.season < ts]
        test = df[df.season == ts].copy()
        if len(test) == 0 or len(train) < 200:
            continue
        reg, win, pod = _fit_fold(train)
        test["pred"] = reg.predict(test[FEATURES])
        test["p_win"] = win.predict_proba(test[FEATURES])[:, 1]
        test["p_podium"] = pod.predict_proba(test[FEATURES])[:, 1]

        model_rows, grid_rows = [], []
        for _, grp in test.groupby(["season", "round"]):
            model_rows.append(race_metrics(grp, "pred", "p_win", "p_podium"))
            # baseline: lower grid is better, so invert for win/podium ranking
            grp = grp.assign(neg_grid=-grp["grid"])
            grid_rows.append(race_metrics(grp, "grid", "neg_grid", "neg_grid"))
        per_season[ts] = {
            "races": len(model_rows),
            "model": {k: round(float(np.mean([r[k] for r in model_rows])), 3) for k in model_rows[0]},
            "grid_baseline": {k: round(float(np.mean([r[k] for r in grid_rows])), 3) for k in grid_rows[0]},
        }
        pooled_model += model_rows
        pooled_grid += grid_rows

    pooled = {
        "model": {k: round(float(np.mean([r[k] for r in pooled_model])), 3) for k in pooled_model[0]},
        "grid_baseline": {k: round(float(np.mean([r[k] for r in pooled_grid])), 3) for k in pooled_grid[0]},
        "races": len(pooled_model),
    }
    return {"pooled": pooled, "by_season": per_season}


# ----------------------------------------------------------------------------- main
def main() -> None:
    df = add_features(pd.read_parquet(DATA))

    backtest = evaluate(df, test_seasons=[2022, 2023, 2024, 2025])
    p = backtest["pooled"]
    print("\n=== Time-series backtest (2022-2025 held out) ===")
    print(f"  races scored:        {p['races']}")
    print(f"  winner top-1:  model {p['model']['winner_hit']:.3f}   grid {p['grid_baseline']['winner_hit']:.3f}")
    print(f"  podium prec@3: model {p['model']['podium_p3']:.3f}   grid {p['grid_baseline']['podium_p3']:.3f}")
    print(f"  rank spearman: model {p['model']['spearman']:.3f}   grid {p['grid_baseline']['spearman']:.3f}")

    # ---- final models trained on everything for the live app ----
    reg, win_clf, podium_clf = _fit_fold(df)

    OUT.mkdir(exist_ok=True)
    joblib.dump(
        {"regressor": reg, "win_clf": win_clf, "podium_clf": podium_clf,
         "features": FEATURES,
         "trained_through": f"{int(df.season.min())}-{int(df.season.max())}"},
        OUT / "f1_model.pkl")

    # Known upstream (Ergast/Jolpica) car-number quirks to correct.
    # Verstappen's permanent number is 33; the source records it as 3.
    number_fixes = {"VER": 33}

    # ---- 2026 current-form snapshot per driver for the interactive app ----
    d26 = df[df.season == 2026]
    latest_round = int(d26["round"].max())
    snap = (d26.sort_values("round").groupby("driver_id").tail(1))

    # per-driver historical average finish at each circuit (all seasons)
    circ_hist = (df.groupby(["driver_code", "circuit_id"])["finish_pos"]
                 .mean().round(2).reset_index())
    hist_by_driver: dict[str, dict] = {}
    for _, r in circ_hist.iterrows():
        hist_by_driver.setdefault(r["driver_code"], {})[r["circuit_id"]] = float(r["finish_pos"])

    form = {}
    for _, r in snap.iterrows():
        form[r["driver_code"]] = {
            "driver_name": r["driver_name"],
            "constructor_name": r["constructor_name"],
            "constructor_id": r["constructor_id"],
            "car_number": number_fixes.get(r["driver_code"], int(r["car_number"])),
            "circuit_hist": hist_by_driver.get(r["driver_code"], {}),
            **{f: (None if pd.isna(r[f]) else float(r[f]))
               for f in ["drv_form3", "drv_form5", "drv_dnf5", "drv_pts_season",
                         "drv_races_prior", "con_form5", "con_dnf5", "con_pts_season"]},
        }

    # circuits on the modern calendar (2024+) for the dropdown
    modern = df[df.season >= 2024][["circuit_id", "circuit_name"]].drop_duplicates()
    circuits = sorted(({"circuit_id": r.circuit_id, "circuit_name": r.circuit_name}
                       for r in modern.itertuples()), key=lambda c: c["circuit_name"])

    (OUT / "driver_form_2026.json").write_text(json.dumps(
        {"through_round": latest_round, "drivers": form, "circuits": circuits}, indent=2))

    metrics = {
        "data": {
            "seasons": f"{int(df.season.min())}-{int(df.season.max())}",
            "races": int(df.groupby('season')['round'].nunique().sum()),
            "driver_race_rows": int(len(df)),
            "source": "Jolpica / Ergast F1 API",
        },
        "model": "HistGradientBoosting (sklearn) — finish-position regressor + podium classifier",
        "backtest": backtest,
        "feature_importance_note": "permutation importance computed separately",
    }
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"\nSaved model + metrics + 2026 form snapshot (through round {latest_round}) to {OUT}/")


if __name__ == "__main__":
    main()
