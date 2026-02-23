"""
TTC Monte Carlo Risk Simulator — FastAPI Backend.

Serves the Monte Carlo simulation as a REST API.
Pre-loads cleaned delay data into memory on startup for fast simulation.

Endpoints:
    GET  /api/stations     — List available stations on Line 1
    POST /api/simulate     — Run Monte Carlo simulation for a route
    GET  /api/risk-matrix  — Avg delay per (station, hour) for Line 1
    GET  /api/weather      — Current Toronto weather + historical risk multiplier
    GET  /health           — Health check

Usage:
    uvicorn api.main:app --reload --port 8000
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation.station_graph import LINE_1_STATIONS, get_route, BASELINE_SEGMENT_TIME
from src.simulation.monte_carlo import MonteCarloSimulator

# ===========================================================================
# Data store — loaded on startup
# ===========================================================================
_delay_data: pd.DataFrame | None = None
_simulator: MonteCarloSimulator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load delay data into memory on startup."""
    global _delay_data, _simulator

    parquet_path = PROJECT_ROOT / "data" / "processed" / "delays_clean.parquet"
    if not parquet_path.exists():
        print(f"ERROR: {parquet_path} not found. Run ETL pipeline first.")
        sys.exit(1)

    print(f"[api] Loading delay data from {parquet_path}...")
    _delay_data = pd.read_parquet(parquet_path)
    _simulator = MonteCarloSimulator(_delay_data, n_runs=10_000)
    print(f"[api] Loaded {len(_delay_data):,} rows. Distributions built.")

    yield

    _delay_data = None
    _simulator = None


# ===========================================================================
# App
# ===========================================================================
app = FastAPI(
    title="TTC Monte Carlo Risk Simulator",
    description="Answers: What is the probability I arrive on time?",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================================================================
# Models
# ===========================================================================
class StationInfo(BaseModel):
    name: str
    index: int
    line: str


class SimulateRequest(BaseModel):
    origin: str = Field(..., examples=["Finch"])
    destination: str = Field(..., examples=["Union"])
    hour: int = Field(..., ge=0, le=23, examples=[8])
    is_weekday: bool = Field(True)
    runs: int = Field(10_000, ge=100, le=50_000)
    threshold: float = Field(35.0, gt=0)


class SimulateResponse(BaseModel):
    origin: str
    destination: str
    n_stations: int
    n_segments: int
    baseline_min: float
    mean_travel_min: float
    median_travel_min: float
    std_travel_min: float
    p5_travel_min: float
    p95_travel_min: float
    p99_travel_min: float
    worst_case_min: float
    threshold_min: float
    prob_on_time: float
    prob_late: float
    histogram_bins: list[float]
    histogram_counts: list[float]


# ===========================================================================
# Endpoints
# ===========================================================================
@app.get("/api/stations", response_model=list[StationInfo])
async def get_stations():
    """List all stations on Line 1 (Yonge-University)."""
    return [
        StationInfo(name=name, index=i, line="YU")
        for i, name in enumerate(LINE_1_STATIONS)
    ]


@app.post("/api/simulate", response_model=SimulateResponse)
async def simulate(req: SimulateRequest):
    """Run a Monte Carlo simulation for a route and return results."""
    if _simulator is None:
        raise HTTPException(status_code=503, detail="Data not loaded yet")

    try:
        route = get_route(req.origin, req.destination, LINE_1_STATIONS)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    n_stations = len(route)
    n_segments = n_stations - 1
    baseline = n_segments * BASELINE_SEGMENT_TIME

    sim = MonteCarloSimulator(_delay_data, n_runs=req.runs) if req.runs != _simulator.n_runs else _simulator
    travel_times = sim.simulate(
        origin=req.origin,
        destination=req.destination,
        departure_hour=req.hour,
        is_weekday=req.is_weekday,
        line=LINE_1_STATIONS,
    )
    stats = sim.summary_stats(travel_times, req.threshold)
    hist_counts, hist_edges = np.histogram(travel_times, bins=50, density=True)

    return SimulateResponse(
        origin=req.origin,
        destination=req.destination,
        n_stations=n_stations,
        n_segments=n_segments,
        baseline_min=baseline,
        mean_travel_min=round(stats["mean_travel_min"], 1),
        median_travel_min=round(stats["median_travel_min"], 1),
        std_travel_min=round(stats["std_travel_min"], 1),
        p5_travel_min=round(stats["p5_travel_min"], 1),
        p95_travel_min=round(stats["p95_travel_min"], 1),
        p99_travel_min=round(stats["p99_travel_min"], 1),
        worst_case_min=round(stats["worst_case_min"], 1),
        threshold_min=req.threshold,
        prob_on_time=round(stats["prob_on_time"], 4),
        prob_late=round(stats["prob_late"], 4),
        histogram_bins=[round(float(x), 2) for x in hist_edges.tolist()],
        histogram_counts=[round(float(x), 6) for x in hist_counts.tolist()],
    )


@app.get("/api/risk-matrix")
async def risk_matrix(is_weekday: bool = True):
    """Return avg delay per (station, hour) for all Line 1 stations."""
    if _delay_data is None:
        raise HTTPException(status_code=503, detail="Data not loaded yet")

    line1_set = set(LINE_1_STATIONS)
    df = _delay_data[_delay_data["station"].isin(line1_set)].copy()
    df = df[df["is_weekday"] == is_weekday]

    grouped = df.groupby(["station", "hour"]).agg(
        avg_delay=("delay_minutes", "mean"),
        total_incidents=("delay_minutes", "count"),
        max_delay=("delay_minutes", "max"),
    ).reset_index()

    matrix = {}
    for station in LINE_1_STATIONS:
        station_data = {}
        for h in range(24):
            row = grouped[(grouped["station"] == station) & (grouped["hour"] == h)]
            if len(row) > 0:
                r = row.iloc[0]
                station_data[str(h)] = {
                    "avg_delay": round(float(r["avg_delay"]), 2),
                    "incidents": int(r["total_incidents"]),
                    "max_delay": float(r["max_delay"]),
                }
            else:
                station_data[str(h)] = {"avg_delay": 0, "incidents": 0, "max_delay": 0}
        matrix[station] = station_data

    return {"stations": LINE_1_STATIONS, "matrix": matrix, "is_weekday": is_weekday}


@app.get("/api/weather")
async def get_weather():
    """
    Fetch current Toronto weather from Open-Meteo and compute a risk multiplier
    based on historical delay patterns under similar conditions.
    """
    import urllib.request
    import json as _json

    if _delay_data is None:
        raise HTTPException(status_code=503, detail="Data not loaded yet")

    url = (
        "https://api.open-meteo.com/v1/forecast?"
        "latitude=43.6532&longitude=-79.3832"
        "&current=temperature_2m,precipitation,snowfall,wind_speed_10m,weather_code"
        "&timezone=America/Toronto"
    )
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            weather = _json.loads(resp.read().decode())
    except Exception:
        return {"available": False, "error": "Could not fetch weather data"}

    current = weather.get("current", {})
    temp = current.get("temperature_2m", 0)
    precip = current.get("precipitation", 0)
    snowfall = current.get("snowfall", 0)
    wind = current.get("wind_speed_10m", 0)
    wmo_code = current.get("weather_code", 0)

    df = _delay_data.copy()
    overall_avg = float(df["delay_minutes"].mean())

    if snowfall > 0 or (temp < 0 and precip > 0):
        subset = df[df["snow_cm"] > 0]
        condition = "snow"
    elif precip > 2:
        subset = df[df["precip_mm"] > 5]
        condition = "heavy_rain"
    elif precip > 0:
        subset = df[(df["precip_mm"] > 0) & (df["precip_mm"] <= 5)]
        condition = "light_rain"
    elif temp < -10:
        subset = df[df["temp_mean_c"] < -10]
        condition = "extreme_cold"
    elif wind > 40:
        subset = df[df["wind_max_kmh"] > 35]
        condition = "high_wind"
    else:
        subset = df[(df["precip_mm"] == 0) & (df["snow_cm"] == 0) & (df["temp_mean_c"] > 0)]
        condition = "clear"

    if len(subset) > 100:
        condition_avg = float(subset["delay_minutes"].mean())
        multiplier = round(condition_avg / overall_avg, 2) if overall_avg > 0 else 1.0
    else:
        condition_avg = overall_avg
        multiplier = 1.0

    wmo_descriptions = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
        80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
        95: "Thunderstorm",
    }

    risk_level = "HIGH" if multiplier >= 1.5 else ("ELEVATED" if multiplier >= 1.2 else "NORMAL")

    return {
        "available": True,
        "temperature_c": temp,
        "precipitation_mm": precip,
        "snowfall_cm": snowfall,
        "wind_speed_kmh": wind,
        "weather_code": wmo_code,
        "weather_description": wmo_descriptions.get(wmo_code, "Unknown"),
        "condition": condition,
        "risk_multiplier": multiplier,
        "risk_level": risk_level,
        "condition_avg_delay_min": round(condition_avg, 1),
        "overall_avg_delay_min": round(overall_avg, 1),
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "data_loaded": _delay_data is not None,
        "rows": len(_delay_data) if _delay_data is not None else 0,
    }
