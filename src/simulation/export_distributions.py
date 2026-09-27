"""
Export the simulator's delay distributions to a static JSON file.

The browser runs the Monte Carlo itself from this file, so the site needs no
backend. The numbers are built the same way as MonteCarloSimulator does:
P(delay) = incidents / (unique dates x trains per hour), and the magnitude
distribution is every positive delay, stored as (minutes, count) pairs.

Usage:
    python -m src.simulation.export_distributions
"""

import json
from pathlib import Path

import pandas as pd

from src.simulation.station_graph import BASELINE_SEGMENT_TIME, LINE_1_STATIONS

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "processed" / "delays_clean.parquet"
OUT = ROOT / "frontend" / "public" / "distributions.json"


def main():
    df = pd.read_parquet(SRC)
    line1 = df[df["station"].isin(set(LINE_1_STATIONS))]

    dates = df.groupby(["station", "hour", "is_weekday"])["date"].nunique()
    dists = {}
    for (station, hour, is_wd), g in line1.groupby(["station", "hour", "is_weekday"]):
        total_trains = dates.get((station, hour, is_wd), 1) * (20 if is_wd else 12)
        p = min(len(g) / total_trains, 1.0)
        vals = g["delay_minutes"][g["delay_minutes"] > 0].value_counts().sort_index()
        pairs = [[int(v), int(c)] for v, c in vals.items()] or [[0, 1]]
        dists[f"{station}|{hour}|{int(is_wd)}"] = [round(p, 6), pairs]

    out = {
        "stations": LINE_1_STATIONS,
        "segment_min": BASELINE_SEGMENT_TIME,
        "rows": int(len(df)),
        "first_date": str(df["date"].min().date()),
        "last_date": str(df["date"].max().date()),
        "d": dists,
    }
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB, {len(dists)} groups)")


if __name__ == "__main__":
    main()
