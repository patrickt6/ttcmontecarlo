"""
Monte Carlo Transit Risk Simulator.

For a given (origin, destination, departure_hour, is_weekday),
runs N simulations of the journey. Each simulation:
  1. Walks the ordered list of intermediate stations.
  2. For each station, samples a possible delay from the
     historical distribution for that station+hour+weekday.
  3. Sums baseline travel time + all sampled delays.

Output: array of N total travel times → probability distribution.
"""

import numpy as np
import pandas as pd

from src.simulation.station_graph import BASELINE_SEGMENT_TIME, get_route


class MonteCarloSimulator:
    """
    Monte Carlo simulation engine for TTC subway travel times.

    Builds empirical delay distributions from historical data and
    runs vectorized simulations over N runs.
    """

    def __init__(self, delay_data: pd.DataFrame, n_runs: int = 10_000):
        """
        Args:
            delay_data: Cleaned delay DataFrame (from delays_clean.parquet).
                        Must have columns: station, hour, is_weekday, delay_minutes, date.
            n_runs: Number of Monte Carlo simulation runs.
        """
        self.delay_data = delay_data
        self.n_runs = n_runs
        self._build_distributions()

    def _build_distributions(self):
        """
        Pre-compute per-(station, hour, is_weekday):
          - P(delay occurs)     → float in [0, 1]
          - delay_minutes array → empirical distribution (only nonzero delays)

        P(delay) is estimated as:
            n_delay_incidents / (n_unique_dates × trains_per_hour)

        Where trains_per_hour ≈ 20 on weekdays, 12 on weekends.
        """
        self.distributions = {}

        # Group delay data
        grouped = self.delay_data.groupby(["station", "hour", "is_weekday"])

        # Count unique dates per group (for estimating total trains)
        date_counts = self.delay_data.groupby(
            ["station", "hour", "is_weekday"]
        )["date"].nunique()

        for (station, hour, is_wd), group in grouped:
            n_delays = len(group)
            n_dates = date_counts.get((station, hour, is_wd), 1)
            trains_per_hour = 20 if is_wd else 12
            total_trains = n_dates * trains_per_hour

            p_delay = min(n_delays / total_trains, 1.0)

            # Only keep positive delay values for the magnitude distribution
            delay_vals = group["delay_minutes"].values
            delay_vals = delay_vals[delay_vals > 0]

            self.distributions[(station, hour, is_wd)] = {
                "p_delay": p_delay,
                "delays": delay_vals if len(delay_vals) > 0 else np.array([0.0]),
            }

    def simulate(
        self,
        origin: str,
        destination: str,
        departure_hour: int,
        is_weekday: bool,
        line: list[str] | None = None,
    ) -> np.ndarray:
        """
        Run Monte Carlo simulation for a journey.

        Args:
            origin: Starting station (canonical name).
            destination: Ending station (canonical name).
            departure_hour: Hour of departure (0–23).
            is_weekday: True for weekday, False for weekend.
            line: Station list for the line (defaults to Line 1).

        Returns:
            Array of shape (n_runs,) with total travel times in minutes.
        """
        route = get_route(origin, destination, line)
        n_segments = len(route) - 1
        baseline = n_segments * BASELINE_SEGMENT_TIME

        # Vectorized simulation: accumulate delays across all stations
        total_delays = np.zeros(self.n_runs)

        for station in route:
            key = (station, departure_hour, is_weekday)
            dist = self.distributions.get(key)
            if dist is None:
                # No historical data for this station/hour/weekday combo
                continue

            # For each run, flip a weighted coin: does a delay happen?
            occurs = np.random.random(self.n_runs) < dist["p_delay"]

            # Sample delay magnitudes from empirical distribution
            sampled = np.random.choice(
                dist["delays"], size=self.n_runs, replace=True
            )

            # Only add delay where it occurred
            total_delays += occurs * sampled

        return baseline + total_delays

    def summary_stats(self, travel_times: np.ndarray, threshold_min: float) -> dict:
        """
        Compute summary statistics for a simulation run.

        Args:
            travel_times: Array of simulated total travel times.
            threshold_min: Maximum acceptable travel time (minutes).

        Returns:
            Dictionary with mean, median, percentiles, and on-time probability.
        """
        return {
            "mean_travel_min": float(np.mean(travel_times)),
            "median_travel_min": float(np.median(travel_times)),
            "std_travel_min": float(np.std(travel_times)),
            "p5_travel_min": float(np.percentile(travel_times, 5)),
            "p95_travel_min": float(np.percentile(travel_times, 95)),
            "p99_travel_min": float(np.percentile(travel_times, 99)),
            "prob_on_time": float(np.mean(travel_times <= threshold_min)),
            "prob_late": float(np.mean(travel_times > threshold_min)),
            "worst_case_min": float(np.max(travel_times)),
        }
