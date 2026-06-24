#!/usr/bin/env python3
"""
F1 data ingestion — Jolpica (Ergast-compatible) REST API.

Pulls per-race results and qualifying for a range of seasons and joins them
into one tidy table at the (season, round, driver) grain. This is the real
training source for the predictor: official classified results, grid slots,
qualifying order, finishing status (Finished / DNF / etc.), and constructor.

The Ergast project was retired; Jolpica (https://api.jolpi.ca/ergast/) is the
maintained, drop-in successor and is what we hit here.

Usage:
    python data/ingest.py                 # default seasons -> data/f1_results.parquet
    python data/ingest.py --start 2014 --end 2026 --out data/f1_results.parquet

Responses are cached under data/_cache/ so re-runs don't re-hit the API.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd
import requests

BASE = "https://api.jolpi.ca/ergast/f1"
CACHE_DIR = Path(__file__).parent / "_cache"
PAGE = 100                     # Jolpica caps page size at 100
SLEEP = 0.35                   # polite spacing; stays well under rate limits
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "f1-race-predictor/2.0 (portfolio project)"})


def _get(path: str) -> dict:
    """GET {BASE}/{path} as JSON, with a small on-disk cache and retries."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = path.replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "-")
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())

    url = f"{BASE}/{path}"
    for attempt in range(5):
        resp = SESSION.get(url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            cache_file.write_text(json.dumps(data))
            time.sleep(SLEEP)
            return data
        if resp.status_code in (429, 500, 502, 503):       # backoff & retry
            wait = 2 ** attempt
            print(f"  {resp.status_code} on {path} — retry in {wait}s")
            time.sleep(wait)
            continue
        resp.raise_for_status()
    raise RuntimeError(f"failed after retries: {url}")


def _paged(resource: str, season: int) -> list[dict]:
    """Fetch every Races page for a season resource (results|qualifying)."""
    races: dict[str, dict] = {}
    offset = 0
    while True:
        data = _get(f"{season}/{resource}.json?limit={PAGE}&offset={offset}")
        mr = data["MRData"]
        page_races = mr["RaceTable"]["Races"]
        for race in page_races:
            rnd = race["round"]
            if rnd not in races:
                races[rnd] = race
            else:                                          # merge paginated rows
                inner = "Results" if resource == "results" else "QualifyingResults"
                races[rnd].setdefault(inner, []).extend(race.get(inner, []))
        total, limit = int(mr["total"]), int(mr["limit"])
        offset += limit
        if offset >= total:
            break
    return list(races.values())


def _quali_seconds(q: dict) -> float | None:
    """Best of Q1/Q2/Q3 in seconds (lower is better)."""
    best = None
    for key in ("Q1", "Q2", "Q3"):
        t = q.get(key)
        if not t or ":" not in t:
            continue
        mins, secs = t.split(":")
        val = int(mins) * 60 + float(secs)
        best = val if best is None or val < best else best
    return best


def build_season(season: int) -> pd.DataFrame:
    """Return one tidy row per (round, driver) for a season."""
    results = _paged("results", season)
    quali_races = {r["round"]: r for r in _paged("qualifying", season)}

    rows = []
    for race in results:
        rnd = race["round"]
        circuit = race["Circuit"]
        q_by_driver = {}
        for q in quali_races.get(rnd, {}).get("QualifyingResults", []):
            q_by_driver[q["Driver"]["driverId"]] = q

        for res in race.get("Results", []):
            drv, con = res["Driver"], res["Constructor"]
            q = q_by_driver.get(drv["driverId"], {})
            status = res["status"]
            finished = status == "Finished" or status.startswith("+")
            rows.append({
                "season": season,
                "round": int(rnd),
                "race_name": race["raceName"],
                "date": race["date"],
                "circuit_id": circuit["circuitId"],
                "circuit_name": circuit["circuitName"],
                "driver_id": drv["driverId"],
                "driver_code": drv.get("code", drv["driverId"][:3].upper()),
                "driver_name": f"{drv['givenName']} {drv['familyName']}",
                "car_number": int(res.get("number", 0)),
                "constructor_id": con["constructorId"],
                "constructor_name": con["name"],
                "grid": int(res.get("grid", 0)),
                "finish_pos": int(res["position"]),
                "points": float(res.get("points", 0)),
                "laps": int(res.get("laps", 0)),
                "status": status,
                "finished": finished,
                "fastest_lap_rank": int(res.get("FastestLap", {}).get("rank", 0)) or None,
                "quali_pos": int(q["position"]) if q.get("position") else None,
                "quali_best_s": _quali_seconds(q) if q else None,
            })
    df = pd.DataFrame(rows)
    print(f"  {season}: {len(df):4d} rows  ({df['round'].nunique()} races)")
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest F1 results from Jolpica/Ergast")
    ap.add_argument("--start", type=int, default=2014)
    ap.add_argument("--end", type=int, default=2026)
    ap.add_argument("--out", default=str(Path(__file__).parent / "f1_results.parquet"))
    args = ap.parse_args()

    print(f"Ingesting F1 {args.start}-{args.end} from {BASE}")
    frames = []
    for season in range(args.start, args.end + 1):
        df = build_season(season)
        if not df.empty:
            frames.append(df)

    full = pd.concat(frames, ignore_index=True).sort_values(["season", "round", "finish_pos"])
    out = Path(args.out)
    full.to_parquet(out, index=False)
    full.to_csv(out.with_suffix(".csv"), index=False)
    print(f"\nWrote {len(full)} rows -> {out}")
    print(f"Seasons: {full['season'].min()}-{full['season'].max()}  "
          f"Races: {full.groupby('season')['round'].nunique().sum()}  "
          f"Drivers: {full['driver_id'].nunique()}")


if __name__ == "__main__":
    main()
