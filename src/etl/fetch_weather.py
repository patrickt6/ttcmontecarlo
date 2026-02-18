"""
Fetch Historical Weather Data from Open-Meteo.

Downloads daily weather data for Toronto covering the full date range
of the delay data, and saves to data/raw/weather/weather.csv.

Usage:
    python -m src.etl.fetch_weather
"""

import os
import glob
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DELAYS_DIR = PROJECT_ROOT / "data" / "raw" / "delays"
RAW_WEATHER_DIR = PROJECT_ROOT / "data" / "raw" / "weather"

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
TORONTO_LAT = 43.6532
TORONTO_LON = -79.3832

DAILY_VARIABLES = [
    "temperature_2m_mean",
    "precipitation_sum",
    "snowfall_sum",
    "rain_sum",
    "wind_speed_10m_max",
]


def detect_date_range() -> tuple[str, str]:
    """
    Scan downloaded delay data files (CSV + XLSX) to find the min/max dates.
    Returns (start_date, end_date) as 'YYYY-MM-DD' strings.
    """
    csv_files = list(RAW_DELAYS_DIR.glob("*.csv"))
    xlsx_files = list(RAW_DELAYS_DIR.glob("*.xlsx"))
    all_files = csv_files + xlsx_files

    if not all_files:
        # Default range if no delay data yet
        print("[fetch_weather] No delay data found, using default range 2014-01-01 to 2025-12-31")
        return "2014-01-01", "2025-12-31"

    all_dates = []
    for f in all_files:
        try:
            if f.suffix.lower() == ".csv":
                df = pd.read_csv(f, usecols=["Date"])
            else:
                df = pd.read_excel(f, usecols=["Date"])
            dates = pd.to_datetime(df["Date"], format="mixed", dayfirst=False)
            all_dates.extend([dates.min(), dates.max()])
        except Exception as e:
            pass  # Silently skip files without Date column (e.g. code descriptions)

    if not all_dates:
        return "2014-01-01", "2025-12-31"

    min_date = min(all_dates).strftime("%Y-%m-%d")
    max_date = max(all_dates).strftime("%Y-%m-%d")
    print(f"[fetch_weather] Detected delay data range: {min_date} to {max_date}")
    return min_date, max_date


def fetch_weather(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch daily weather from Open-Meteo archive API.
    The API has a max range limit, so we chunk into yearly requests if needed.
    """
    all_frames = []

    start_year = int(start_date[:4])
    end_year = int(end_date[:4])

    for year in range(start_year, end_year + 1):
        chunk_start = f"{year}-01-01" if year > start_year else start_date
        chunk_end = f"{year}-12-31" if year < end_year else end_date

        params = {
            "latitude": TORONTO_LAT,
            "longitude": TORONTO_LON,
            "start_date": chunk_start,
            "end_date": chunk_end,
            "daily": ",".join(DAILY_VARIABLES),
            "timezone": "America/Toronto",
        }

        print(f"  Fetching weather for {chunk_start} to {chunk_end}...")
        try:
            resp = requests.get(OPEN_METEO_URL, params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            if "daily" in data:
                df = pd.DataFrame(data["daily"])
                df.rename(columns={"time": "date"}, inplace=True)
                all_frames.append(df)
            else:
                print(f"    WARNING: No daily data returned for {year}")
        except requests.RequestException as e:
            print(f"    WARNING: Failed to fetch weather for {year}: {e}")

    if not all_frames:
        raise RuntimeError("Failed to fetch any weather data")

    weather = pd.concat(all_frames, ignore_index=True)
    weather["date"] = pd.to_datetime(weather["date"])
    weather = weather.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
    return weather


def main():
    """Main entry point: fetch weather data for the delay data date range."""
    print("=" * 60)
    print("TTC Monte Carlo Risk Simulator — Fetch Weather Data")
    print("=" * 60)

    output_path = RAW_WEATHER_DIR / "weather.csv"
    if output_path.exists():
        print(f"[fetch_weather] Weather file already exists: {output_path}")
        print("[fetch_weather] Delete it to re-fetch. Skipping.")
        return

    start_date, end_date = detect_date_range()
    weather = fetch_weather(start_date, end_date)

    RAW_WEATHER_DIR.mkdir(parents=True, exist_ok=True)
    weather.to_csv(output_path, index=False)

    print(f"\n✅ Done. Weather data saved to {output_path}")
    print(f"   Date range: {weather['date'].min()} to {weather['date'].max()}")
    print(f"   Total rows: {len(weather):,}")
    print(f"   Columns: {list(weather.columns)}")


if __name__ == "__main__":
    main()
