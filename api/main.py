"""
TTC Monte Carlo Risk Simulator — FastAPI Backend.

Serves the Monte Carlo simulation engine over HTTP.

Endpoints:
    GET  /api/stations  — List available stations on Line 1

Usage:
    uvicorn api.main:app --reload --port 8000
"""

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation.station_graph import LINE_1_STATIONS

app = FastAPI(
    title="TTC Monte Carlo Risk Simulator",
    description="Answers: What is the probability I arrive on time?",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StationInfo(BaseModel):
    name: str
    index: int
    line: str


@app.get("/api/stations", response_model=list[StationInfo])
async def get_stations():
    """List all stations on Line 1 (Yonge-University)."""
    return [
        StationInfo(name=name, index=i, line="YU")
        for i, name in enumerate(LINE_1_STATIONS)
    ]
