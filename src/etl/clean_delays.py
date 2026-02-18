"""
Clean TTC Delay Data — Station Name Canonicalization + Code Categorization.

Loads all raw delay CSVs, applies Regex-based station name cleaning and
delay code categorization, merges weather data, and outputs a clean Parquet file.

Usage:
    python -m src.etl.clean_delays
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DELAYS_DIR = PROJECT_ROOT / "data" / "raw" / "delays"
RAW_WEATHER_DIR = PROJECT_ROOT / "data" / "raw" / "weather"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# ============================================================================
# Station Name Canonical Mapping (Regex → Clean Name)
# Covers all 69 stations across Lines 1 and 2
# ============================================================================
STATION_CANONICAL = {
    # --- LINE 1 YONGE-UNIVERSITY (38 stations) ---
    r"(?i)^finch\s*(stn|station)?$": "Finch",
    r"(?i)north\s*york\s*cent": "North York Centre",
    r"(?i)sheppard[\s-]*yonge": "Sheppard-Yonge",
    r"(?i)^york\s*mills": "York Mills",
    r"(?i)^lawrence\s*(stn|station)?$": "Lawrence",
    r"(?i)^eglinton\s*(stn|station)?$": "Eglinton",
    r"(?i)^davisville": "Davisville",
    r"(?i)^st\.?\s*clair\s*(stn|station)?$": "St Clair",
    r"(?i)^summerhill": "Summerhill",
    r"(?i)^rosedale": "Rosedale",
    r"(?i)bloor[\s-]*yonge": "Bloor-Yonge",
    r"(?i)^wellesley": "Wellesley",
    r"(?i)^college": "College",
    r"(?i)^(dundas\s*(stn|station)?|tmu)$": "TMU",
    r"(?i)^queen\s*(stn|station)?$": "Queen",
    r"(?i)^king\s*(stn|station)?$": "King",
    r"(?i)^union\s*(stn|station)?$": "Union",
    r"(?i)^st\.?\s*andrew": "St Andrew",
    r"(?i)^osgoode": "Osgoode",
    r"(?i)^st\.?\s*patrick": "St Patrick",
    r"(?i)queen'?s?\s*park": "Queen's Park",
    r"(?i)^museum": "Museum",
    r"(?i)^st\.?\s*george": "St George",
    r"(?i)^spadina\s*(stn|station)?$": "Spadina",
    r"(?i)^dupont": "Dupont",
    r"(?i)^st\.?\s*clair\s*w": "St Clair West",
    r"(?i)^(eglinton\s*w|cedarvale)": "Cedarvale",
    r"(?i)^glencairn": "Glencairn",
    r"(?i)^lawrence\s*w": "Lawrence West",
    r"(?i)^yorkdale": "Yorkdale",
    r"(?i)^wilson": "Wilson",
    r"(?i)sheppard\s*w|downsview\s*(stn|station)?$": "Sheppard West",
    r"(?i)downsview\s*park": "Downsview Park",
    r"(?i)finch\s*w": "Finch West",
    r"(?i)york\s*univ": "York University",
    r"(?i)pioneer\s*vill": "Pioneer Village",
    r"(?i)(hwy|highway)\s*407": "Highway 407",
    r"(?i)vaughan\s*metro": "Vaughan Metropolitan Centre",

    # --- LINE 2 BLOOR-DANFORTH (31 stations) ---
    r"(?i)^kipling": "Kipling",
    r"(?i)^islington": "Islington",
    r"(?i)^royal\s*york": "Royal York",
    r"(?i)^old\s*mill": "Old Mill",
    r"(?i)^jane\s*(stn|station)?$": "Jane",
    r"(?i)^runnymede": "Runnymede",
    r"(?i)^high\s*park": "High Park",
    r"(?i)^keele": "Keele",
    r"(?i)^dundas\s*w": "Dundas West",
    r"(?i)^lansdowne": "Lansdowne",
    r"(?i)^dufferin": "Dufferin",
    r"(?i)^ossington": "Ossington",
    r"(?i)^christie": "Christie",
    r"(?i)^bathurst": "Bathurst",
    r"(?i)^bay\s*(stn|station)?$": "Bay",
    r"(?i)^sherbourne": "Sherbourne",
    r"(?i)^castle\s*frank": "Castle Frank",
    r"(?i)^broadview": "Broadview",
    r"(?i)^chester": "Chester",
    r"(?i)^pape": "Pape",
    r"(?i)^donlands": "Donlands",
    r"(?i)^greenwood": "Greenwood",
    r"(?i)^coxwell": "Coxwell",
    r"(?i)^woodbine": "Woodbine",
    r"(?i)^main\s*st": "Main Street",
    r"(?i)^victoria\s*park": "Victoria Park",
    r"(?i)^warden": "Warden",
    r"(?i)^kennedy": "Kennedy",

    # --- LINE 3 SCARBOROUGH (if present in data) ---
    r"(?i)^scarborough\s*cent": "Scarborough Centre",
    r"(?i)^mccowan": "McCowan",
    r"(?i)^midland": "Midland",
    r"(?i)^ellesmere": "Ellesmere",
    r"(?i)^lawrence\s*e": "Lawrence East",

    # --- LINE 4 SHEPPARD (if present in data) ---
    r"(?i)^don\s*mills": "Don Mills",
    r"(?i)^leslie": "Leslie",
    r"(?i)^bessarion": "Bessarion",
    r"(?i)^bayview": "Bayview",
}


def clean_station(raw: str) -> str:
    """Map a messy station name to its canonical form using Regex."""
    if pd.isna(raw) or str(raw).strip() == "":
        return "UNKNOWN"
    raw = str(raw).strip()
    for pattern, canonical in STATION_CANONICAL.items():
        if re.search(pattern, raw):
            return canonical
    return raw.strip().title()


# ============================================================================
# Delay Code Categorization (Regex → 6 categories + Miscellaneous)
# ============================================================================
CODE_CATEGORIES = {
    "Mechanical": r"(?i)^(MU|ME|MR|MT)",
    "Signal/Power": r"(?i)^(SU|PU|SG|PW)",
    "Disorderly Patron": r"(?i)(DIS|ASSAULT|SECURITY|TRESPASS|UNAUTH|BOMB)",
    "Medical": r"(?i)(MED|ILL|INJUR|SICK|EMERG)",
    "Weather/External": r"(?i)(WEATHER|FLOOD|SNOW|ICE|FIRE|SMOKE|WATER|POWER\s*OUT)",
    "Operational": r"(?i)^(OP|SPEED|DOOR|CREW|LATE|TRAIN|ATC)",
}


def categorize_code(code: str) -> str:
    """Map a TTC delay code to one of 6 categories (or Miscellaneous)."""
    if pd.isna(code) or str(code).strip() == "":
        return "Unknown"
    code = str(code).strip()
    for category, pattern in CODE_CATEGORIES.items():
        if re.search(pattern, code):
            return category
    return "Miscellaneous"


# ============================================================================
# Main ETL Pipeline
# ============================================================================

def load_raw_delays() -> pd.DataFrame:
    """Load and concatenate all raw delay data files (CSV + XLSX)."""
    csv_files = sorted(RAW_DELAYS_DIR.glob("*.csv"))
    xlsx_files = sorted(RAW_DELAYS_DIR.glob("*.xlsx"))
    all_files = csv_files + xlsx_files

    if not all_files:
        raise FileNotFoundError(
            f"No data files found in {RAW_DELAYS_DIR}. "
            "Run `python -m src.etl.fetch_delays` first."
        )

    frames = []
    for f in all_files:
        try:
            if f.suffix.lower() == ".csv":
                df = pd.read_csv(f)
            else:
                df = pd.read_excel(f)
            frames.append(df)
            print(f"  Loaded {f.name}: {len(df):,} rows, cols={list(df.columns)}")
        except Exception as e:
            print(f"  WARNING: Failed to load {f.name}: {e}")

    raw = pd.concat(frames, ignore_index=True)
    print(f"  Total raw rows: {len(raw):,}")
    return raw


def load_weather() -> pd.DataFrame | None:
    """Load cached weather data if available."""
    weather_path = RAW_WEATHER_DIR / "weather.csv"
    if not weather_path.exists():
        print("[clean_delays] No weather data found. Run `python -m src.etl.fetch_weather` first.")
        print("[clean_delays] Proceeding without weather columns.")
        return None

    weather = pd.read_csv(weather_path)
    weather["date"] = pd.to_datetime(weather["date"])
    print(f"  Loaded weather data: {len(weather):,} rows")
    return weather


def clean_delays(raw: pd.DataFrame, weather: pd.DataFrame | None) -> pd.DataFrame:
    """Apply all cleaning transformations and merge weather."""
    df = raw.copy()

    # --- Parse dates ---
    print("[clean_delays] Parsing dates...")
    df["date"] = pd.to_datetime(df["Date"], format="mixed", dayfirst=False, errors="coerce")

    # --- Parse time and extract hour ---
    print("[clean_delays] Parsing times...")
    df["time_str"] = df["Time"].astype(str).str.strip()
    df["hour"] = pd.to_datetime(df["time_str"], format="%H:%M", errors="coerce").dt.hour
    mask = df["hour"].isna()
    if mask.any():
        df.loc[mask, "hour"] = pd.to_datetime(
            df.loc[mask, "time_str"], format="mixed", errors="coerce"
        ).dt.hour
    df["hour"] = df["hour"].fillna(-1).astype(int)

    # --- Day of week and is_weekday ---
    df["day_of_week"] = df["Day"].astype(str).str.strip()
    weekdays = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}
    df["is_weekday"] = df["day_of_week"].isin(weekdays)

    # --- Clean station names ---
    print("[clean_delays] Cleaning station names...")
    df["station"] = df["Station"].apply(clean_station)
    n_unique = df["station"].nunique()
    print(f"  Unique stations after cleaning: {n_unique}")

    # --- Line ---
    df["line"] = df["Line"].astype(str).str.strip().str.upper()

    # --- Bound ---
    df["bound"] = df["Bound"].astype(str).str.strip().str.upper()

    # --- Delay and gap minutes ---
    df["delay_minutes"] = pd.to_numeric(df["Min Delay"], errors="coerce").fillna(0.0)
    df["gap_minutes"] = pd.to_numeric(df["Min Gap"], errors="coerce").fillna(0.0)

    # --- Code categorization ---
    print("[clean_delays] Categorizing delay codes...")
    df["code_raw"] = df["Code"].astype(str).str.strip()
    df["code_category"] = df["Code"].apply(categorize_code)

    cat_counts = df["code_category"].value_counts()
    print("  Code category distribution:")
    for cat, count in cat_counts.items():
        print(f"    {cat}: {count:,}")

    # --- Merge weather ---
    if weather is not None:
        print("[clean_delays] Merging weather data...")
        weather_cols = weather.rename(columns={
            "temperature_2m_mean": "temp_mean_c",
            "precipitation_sum": "precip_mm",
            "snowfall_sum": "snow_cm",
            "rain_sum": "rain_mm",
            "wind_speed_10m_max": "wind_max_kmh",
        })
        df = df.merge(weather_cols, on="date", how="left")
    else:
        df["temp_mean_c"] = np.nan
        df["precip_mm"] = np.nan
        df["snow_cm"] = np.nan
        df["rain_mm"] = np.nan
        df["wind_max_kmh"] = np.nan

    # --- Select final columns ---
    output_columns = [
        "date", "time_str", "hour", "day_of_week", "is_weekday",
        "station", "line", "bound",
        "delay_minutes", "gap_minutes",
        "code_raw", "code_category",
        "temp_mean_c", "precip_mm", "snow_cm", "wind_max_kmh",
    ]
    output_columns = [c for c in output_columns if c in df.columns]
    result = df[output_columns].copy()
    result = result.dropna(subset=["date"])

    return result


def main():
    """Main entry point: clean raw delays and output Parquet."""
    print("=" * 60)
    print("TTC Monte Carlo Risk Simulator — Clean Delay Data")
    print("=" * 60)

    print("\n[1/3] Loading raw delay CSVs...")
    raw = load_raw_delays()

    print("\n[2/3] Loading weather data...")
    weather = load_weather()

    print("\n[3/3] Cleaning and transforming...")
    clean = clean_delays(raw, weather)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PROCESSED_DIR / "delays_clean.parquet"
    clean.to_parquet(output_path, index=False)

    print(f"\nDone. Clean data saved to {output_path}")
    print(f"   Total clean rows: {len(clean):,}")
    print(f"   Date range: {clean['date'].min()} to {clean['date'].max()}")
    print(f"   Columns: {list(clean.columns)}")


if __name__ == "__main__":
    main()
