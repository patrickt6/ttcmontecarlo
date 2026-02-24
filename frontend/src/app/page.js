"use client";

import { useState, useEffect } from "react";

export default function Home() {
  const [stations, setStations] = useState([]);
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [arriveHour, setArriveHour] = useState(9);
  const [arriveMinute, setArriveMinute] = useState(0);
  const [isWeekday, setIsWeekday] = useState(true);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [weather, setWeather] = useState(null);

  // ── INIT ───────────────────────────────────────────
  useEffect(() => {
    fetch("/api/weather")
      .then((r) => r.json())
      .then((d) => { if (d.available) setWeather(d); })
      .catch(() => {});

    fetch("/api/stations")
      .then((r) => r.json())
      .then((data) => {
        setStations(data);
        if (data.length >= 2) {
          setOrigin("Finch");
          setDestination("Union");
        }
      })
      .catch(() => setError("Failed to load stations. Is the API running?"));
  }, []);

  // ── FORECAST ───────────────────────────────────────
  useEffect(() => {
    if (!origin || !destination || origin === destination) {
      setResult(null);
      return;
    }

    const run = async () => {
      setLoading(true);
      setError(null);

      try {
        const resp = await fetch("/api/leave-by", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            origin,
            destination,
            arrive_by_hour: arriveHour,
            arrive_by_minute: arriveMinute,
            is_weekday: isWeekday,
            confidence: 0.85,
          }),
        });

        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || "Forecast failed.");
        }

        const data = await resp.json();

        if (!data.recommendation) {
          throw new Error("No safe departure found for this route and timeline.");
        }

        const arriveMins = arriveHour * 60 + arriveMinute;
        const departMins = arriveMins - data.recommendation.p95_travel_min;
        setResult({ ...data, exact_depart_mins: departMins });
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };

    const timer = setTimeout(run, 300);
    return () => clearTimeout(timer);
  }, [origin, destination, arriveHour, arriveMinute, isWeekday]);

  // ── HELPERS ────────────────────────────────────────
  const fmt = (totalMins) => {
    let m = totalMins;
    while (m < 0) m += 1440;
    while (m >= 1440) m -= 1440;
    const h = Math.floor(m / 60);
    const min = Math.floor(m % 60).toString().padStart(2, "0");
    const ampm = h >= 12 ? "PM" : "AM";
    const disp = h % 12 === 0 ? 12 : h % 12;
    return `${disp}:${min} ${ampm}`;
  };

  const pct = (p) => `${(p * 100).toFixed(0)}%`;

  const riskRating = (probOnTime) => {
    if (probOnTime >= 0.85) return "low";
    if (probOnTime >= 0.70) return "moderate";
    return "high";
  };

  // ── HISTOGRAM ──────────────────────────────────────
  const renderHistogram = () => {
    const rec = result?.recommendation;
    if (!rec?.histogram_bins) return null;

    const { histogram_bins: bins, histogram_counts: counts, p95_travel_min: p95 } = rec;
    const maxCount = Math.max(...counts);

    return (
      <div className="hist-section">
        <div className="hist-label">Travel time distribution — 10,000 simulated trips</div>
        <div className="hist-bars">
          {counts.map((c, i) => (
            <div
              key={i}
              className={`hist-bar${bins[i] > p95 ? " danger" : ""}`}
              style={{ height: `${maxCount > 0 ? (c / maxCount) * 100 : 0}%` }}
            />
          ))}
        </div>
        <div className="hist-axis">
          <span>{Math.round(bins[0])} min</span>
          <span>{Math.round(bins[bins.length - 1])} min</span>
        </div>
      </div>
    );
  };

  // ── RENDER ─────────────────────────────────────────
  return (
    <div className="page">
      <h1>TTC Monte Carlo Risk Simulator</h1>
      <p className="subtitle">
        Line 1 · 10,000 simulated journeys · historical delays 2014–2025
        {weather && (
          <span> · {weather.temperature_c.toFixed(0)}°C, {weather.weather_description.toLowerCase()}{weather.risk_level !== "NORMAL" ? ` · ${weather.risk_level.toLowerCase()} delay risk` : ""}</span>
        )}
      </p>

      <div className="field">
        <label>Origin</label>
        <select value={origin} onChange={(e) => setOrigin(e.target.value)}>
          {stations.map((s) => (
            <option key={s.name} value={s.name}>{s.name}</option>
          ))}
        </select>
      </div>

      <div className="field">
        <label>Destination</label>
        <select value={destination} onChange={(e) => setDestination(e.target.value)}>
          {stations.map((s) => (
            <option key={s.name} value={s.name}>{s.name}</option>
          ))}
        </select>
      </div>

      <div className="field-row">
        <div className="field">
          <label>Arrive by (hour)</label>
          <select value={arriveHour} onChange={(e) => setArriveHour(parseInt(e.target.value))}>
            {Array.from({ length: 24 }, (_, i) => (
              <option key={i} value={i}>{fmt(i * 60)}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Arrive by (minute)</label>
          <select value={arriveMinute} onChange={(e) => setArriveMinute(parseInt(e.target.value))}>
            {[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55].map((m) => (
              <option key={m} value={m}>{m.toString().padStart(2, "0")}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="field">
        <label>Day type</label>
        <div className="daytype">
          <label>
            <input type="radio" name="daytype" checked={isWeekday} onChange={() => setIsWeekday(true)} />
            Weekday
          </label>
          <label>
            <input type="radio" name="daytype" checked={!isWeekday} onChange={() => setIsWeekday(false)} />
            Weekend
          </label>
        </div>
      </div>

      <hr />

      {loading && <p className="status">Simulating 10,000 trips...</p>}
      {error && <p className="error">{error}</p>}

      {result && !loading && (
        <>
          <div className="depart-time">{fmt(result.exact_depart_mins)}</div>
          <div className="depart-sub">
            Depart by to arrive at {result.arrive_by} with 85% confidence
          </div>

          <table className="result-table">
            <tbody>
              <tr>
                <td>Route</td>
                <td>{origin} → {destination}</td>
              </tr>
              <tr>
                <td>Travel time (P95)</td>
                <td>{result.recommendation.p95_travel_min} min</td>
              </tr>
              <tr>
                <td>Travel time (mean)</td>
                <td>{result.recommendation.mean_travel_min} min</td>
              </tr>
              <tr>
                <td>On-time probability</td>
                <td className={result.recommendation.prob_on_time < 0.7 ? "warn" : ""}>
                  {pct(result.recommendation.prob_on_time)}
                </td>
              </tr>
              <tr>
                <td>Late probability</td>
                <td className={result.recommendation.prob_late > 0.3 ? "warn" : ""}>
                  {pct(result.recommendation.prob_late)}
                </td>
              </tr>
              <tr>
                <td>Risk rating</td>
                <td className={riskRating(result.recommendation.prob_on_time) === "high" ? "warn" : ""}>
                  {riskRating(result.recommendation.prob_on_time)}
                </td>
              </tr>
            </tbody>
          </table>

          {renderHistogram()}
        </>
      )}
    </div>
  );
}
