"""
CLI Entry Point — Run Monte Carlo Simulation.

Usage:
    python -m src.simulation.run_simulation \
        --origin "Finch" \
        --destination "Union" \
        --hour 8 \
        --weekday \
        --runs 10000 \
        --threshold 35
"""

import argparse
import sys
import pandas as pd
from pathlib import Path

from src.simulation.monte_carlo import MonteCarloSimulator
from src.simulation.station_graph import LINE_1_STATIONS, get_route
from src.viz.plot_histogram import plot_travel_time_histogram

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "output"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TTC Monte Carlo Risk Simulator — Run a journey simulation."
    )
    parser.add_argument(
        "--origin", type=str, required=True,
        help="Origin station (canonical name, e.g. 'Finch')"
    )
    parser.add_argument(
        "--destination", type=str, required=True,
        help="Destination station (canonical name, e.g. 'Union')"
    )
    parser.add_argument(
        "--hour", type=int, required=True,
        help="Departure hour (0–23)"
    )
    parser.add_argument(
        "--weekday", action="store_true", default=False,
        help="Simulate a weekday departure (default: weekend)"
    )
    parser.add_argument(
        "--weekend", action="store_true", default=False,
        help="Simulate a weekend departure"
    )
    parser.add_argument(
        "--runs", type=int, default=10_000,
        help="Number of Monte Carlo runs (default: 10,000)"
    )
    parser.add_argument(
        "--threshold", type=float, default=35.0,
        help="On-time threshold in minutes (default: 35.0)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Resolve weekday/weekend
    if args.weekend:
        is_weekday = False
    elif args.weekday:
        is_weekday = True
    else:
        is_weekday = True  # default to weekday

    day_type = "Weekday" if is_weekday else "Weekend"

    # Load cleaned data
    parquet_path = PROCESSED_DIR / "delays_clean.parquet"
    if not parquet_path.exists():
        print(f"ERROR: Clean data not found at {parquet_path}")
        print("Run the ETL pipeline first:")
        print("  python -m src.etl.fetch_delays")
        print("  python -m src.etl.fetch_weather")
        print("  python -m src.etl.clean_delays")
        sys.exit(1)

    print("Loading delay data...")
    delay_data = pd.read_parquet(parquet_path)

    # Validate stations exist on Line 1
    try:
        route = get_route(args.origin, args.destination, LINE_1_STATIONS)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Run simulation
    print(f"Running {args.runs:,} simulations...")
    simulator = MonteCarloSimulator(delay_data, n_runs=args.runs)
    travel_times = simulator.simulate(
        origin=args.origin,
        destination=args.destination,
        departure_hour=args.hour,
        is_weekday=is_weekday,
        line=LINE_1_STATIONS,
    )

    # Compute stats
    stats = simulator.summary_stats(travel_times, args.threshold)

    # Generate output filename
    origin_slug = args.origin.lower().replace(" ", "_").replace("'", "")
    dest_slug = args.destination.lower().replace(" ", "_").replace("'", "")
    hist_filename = f"simulation_{origin_slug}_to_{dest_slug}_{args.hour:02d}h.png"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    hist_path = OUTPUT_DIR / hist_filename

    # Plot histogram
    route_info = {
        "origin": args.origin,
        "destination": args.destination,
        "hour": args.hour,
        "day_type": day_type,
        "runs": args.runs,
    }
    plot_travel_time_histogram(travel_times, args.threshold, route_info, str(hist_path))

    # Print results
    print()
    print("=" * 50)
    print("  TTC Monte Carlo Risk Simulation")
    print("=" * 50)
    print(f"  Route:       {args.origin} → {args.destination} (Line 1 Yonge-University)")
    print(f"  Stations:    {len(route)} ({len(route) - 1} segments)")
    print(f"  Departure:   {args.hour:02d}:00, {day_type}")
    print(f"  Runs:        {args.runs:,}")
    print(f"  Threshold:   {args.threshold:.1f} min")
    print()
    print("  --- Results ---")
    print(f"  Mean travel:      {stats['mean_travel_min']:.1f} min")
    print(f"  Median travel:    {stats['median_travel_min']:.1f} min")
    print(f"  Std dev:          {stats['std_travel_min']:.1f} min")
    print(f"  P5  (best case):  {stats['p5_travel_min']:.1f} min")
    print(f"  P95 (worst case): {stats['p95_travel_min']:.1f} min")
    print(f"  P99:              {stats['p99_travel_min']:.1f} min")
    print(f"  Worst run:        {stats['worst_case_min']:.1f} min")
    print()

    p_on_time = stats["prob_on_time"] * 100
    p_late = stats["prob_late"] * 100
    if p_on_time >= 80:
        print(f"  ✅ P(on-time ≤ {args.threshold:.0f} min): {p_on_time:.1f}%")
    else:
        print(f"  ⚠️  P(on-time ≤ {args.threshold:.0f} min): {p_on_time:.1f}%")
    print(f"  ⚠️  P(late > {args.threshold:.0f} min):    {p_late:.1f}%")
    print()
    print(f"  Histogram saved to: {hist_path}")
    print("=" * 50)


if __name__ == "__main__":
    main()
