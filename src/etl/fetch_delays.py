"""
Fetch TTC Subway Delay Data from Open Data Toronto.

Downloads all available CSV and XLSX resources from the TTC Subway Delay Data
package and saves them to data/raw/delays/.

Historical data (2014–2024) is in XLSX format; 2025+ is in CSV.
Both are downloaded and the clean_delays step handles both formats.

Usage:
    python -m src.etl.fetch_delays
"""

import os
import sys
import requests
import pandas as pd
from pathlib import Path

# Project root = 2 levels up from this file (src/etl/fetch_delays.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DELAYS_DIR = PROJECT_ROOT / "data" / "raw" / "delays"

BASE_URL = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
PACKAGE_ID = "996cfe8d-fb35-40ce-b569-698d51fc683b"  # TTC Subway Delay Data

# Skip non-data resources (readme, code descriptions, XML, JSON)
SKIP_KEYWORDS = ["readme", "code_description", "code-description", "codes"]


def fetch_package_resources(package_id: str) -> list[dict]:
    """List all resources in a CKAN package."""
    url = f"{BASE_URL}/api/3/action/package_show?id={package_id}"
    print(f"[fetch_delays] Querying package: {package_id}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()["result"]["resources"]


def search_for_package() -> str:
    """Fallback: search catalogue for TTC subway delay data."""
    url = f"{BASE_URL}/api/3/action/package_search"
    params = {"q": "ttc subway delay", "rows": 5}
    print("[fetch_delays] Primary package ID may be stale, searching catalogue...")
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    results = resp.json()["result"]["results"]
    if not results:
        raise RuntimeError(
            "Could not find TTC Subway Delay Data in Open Data Toronto catalogue. "
            "Please download files manually and place them in data/raw/delays/"
        )
    pkg_id = results[0]["id"]
    print(f"[fetch_delays] Found package: {results[0]['title']} (id={pkg_id})")
    return pkg_id


def is_delay_data_resource(resource: dict) -> bool:
    """Filter for actual delay data files (not readme, codes, XML, JSON)."""
    fmt = resource.get("format", "").upper()
    name = resource.get("name", "").lower()

    # Only CSV and XLSX formats
    if fmt not in ("CSV", "XLSX"):
        return False

    # Skip code descriptions and readmes
    for skip in SKIP_KEYWORDS:
        if skip in name.replace(" ", "_").lower():
            return False

    # Must contain "delay" in the name
    if "delay" not in name:
        return False

    return True


def download_resources(resources: list[dict], output_dir: Path) -> list[Path]:
    """Download all delay data resources (CSV + XLSX). Returns list of saved file paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    data_resources = [r for r in resources if is_delay_data_resource(r)]
    print(f"[fetch_delays] Found {len(data_resources)} delay data resources to download")

    for i, r in enumerate(data_resources, 1):
        name = r.get("name", f"delays_{i}").replace(" ", "_")
        fmt = r.get("format", "CSV").upper()
        ext = ".csv" if fmt == "CSV" else ".xlsx"

        # Ensure correct extension
        if not name.lower().endswith(ext):
            name += ext
        filepath = output_dir / name

        if filepath.exists():
            print(f"  [{i}/{len(data_resources)}] SKIP (exists): {name}")
            saved.append(filepath)
            continue

        print(f"  [{i}/{len(data_resources)}] Downloading: {name} ({fmt})")
        try:
            resp = requests.get(r["url"], timeout=120)
            resp.raise_for_status()
            filepath.write_bytes(resp.content)
            saved.append(filepath)
        except requests.RequestException as e:
            print(f"  WARNING: Failed to download {name}: {e}")

    return saved


def main():
    """Main entry point: fetch all TTC delay data files."""
    print("=" * 60)
    print("TTC Monte Carlo Risk Simulator — Fetch Delay Data")
    print("=" * 60)

    # Try primary package ID first, fallback to search
    try:
        resources = fetch_package_resources(PACKAGE_ID)
    except (requests.RequestException, KeyError):
        pkg_id = search_for_package()
        resources = fetch_package_resources(pkg_id)

    saved_files = download_resources(resources, RAW_DELAYS_DIR)

    print(f"\n✅ Done. {len(saved_files)} files in {RAW_DELAYS_DIR}")

    # Quick summary: count total rows
    total_rows = 0
    for f in saved_files:
        try:
            if f.suffix.lower() == ".csv":
                df = pd.read_csv(f)
            else:
                df = pd.read_excel(f)
            total_rows += len(df)
            print(f"   {f.name}: {len(df):,} rows")
        except Exception as e:
            print(f"   {f.name}: ERROR reading — {e}")
    print(f"   TOTAL: {total_rows:,} rows")


if __name__ == "__main__":
    main()
