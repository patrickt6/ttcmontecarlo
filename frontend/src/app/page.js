"use client";

import { useState, useEffect } from "react";

const UNIVERSITY_BRANCH = [
  "Vaughan Metropolitan Centre",
  "Highway 407",
  "Pioneer Village",
  "York University",
  "Finch West",
  "Downsview Park",
  "Sheppard West",
  "Wilson",
  "Yorkdale",
  "Lawrence West",
  "Glencairn",
  "Cedarvale",
  "St Clair West",
  "Dupont",
  "Spadina",
  "St George",
  "Museum",
  "Queen's Park",
  "St Patrick",
  "Osgoode",
  "St Andrew",
  "Union",
];

const YONGE_BRANCH = [
  "Finch",
  "North York Centre",
  "Sheppard-Yonge",
  "York Mills",
  "Lawrence",
  "Eglinton",
  "Davisville",
  "St Clair",
  "Summerhill",
  "Rosedale",
  "Bloor-Yonge",
  "Wellesley",
  "College",
  "TMU",
  "Queen",
  "King",
  "Union",
];

const defaultArriveBy = () => {
  const now = new Date();
  const total = now.getHours() * 60 + now.getMinutes() + 45;
  return {
    hour: Math.floor(total / 60) % 24,
    minute: Math.round((total % 60) / 5) * 5 % 60,
  };
};

export default function Home() {
  const [mode, setMode] = useState("leave-now");
  const [origin, setOrigin] = useState("Finch");
  const [destination, setDestination] = useState("Union");
  const [selectionMode, setSelectionMode] = useState("origin");
  const [arriveHour, setArriveHour] = useState(() => defaultArriveBy().hour);
  const [arriveMinute, setArriveMinute] = useState(() => defaultArriveBy().minute);
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
        let data;

        if (mode === "leave-now") {
          const now = new Date();
          const resp = await fetch("/api/simulate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              origin,
              destination,
              hour: now.getHours(),
              is_weekday: isWeekday,
              threshold: 9999,
            }),
          });
          if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || "Simulation failed.");
          }
          const sim = await resp.json();
          const departMins = now.getHours() * 60 + now.getMinutes();
          data = { type: "leave-now", depart_mins: departMins, ...sim };

        } else {
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
          const leaveBy = await resp.json();
          if (!leaveBy.recommendation) {
            throw new Error("No safe departure found for this route and timeline.");
          }
          const arriveMins = arriveHour * 60 + arriveMinute;
          const departMins = arriveMins - leaveBy.recommendation.p95_travel_min;
          data = { type: "arrive-by", exact_depart_mins: departMins, ...leaveBy };
        }

        setResult(data);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };

    const timer = setTimeout(run, 300);
    return () => clearTimeout(timer);
  }, [origin, destination, arriveHour, arriveMinute, isWeekday, mode]);

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

  const resetToNow = () => {
    const { hour, minute } = defaultArriveBy();
    setArriveHour(hour);
    setArriveMinute(minute);
  };

  const riskRating = (probOnTime) => {
    if (probOnTime >= 0.85) return "low";
    if (probOnTime >= 0.70) return "moderate";
    return "high";
  };

  // ── STATION PICKER ─────────────────────────────────
  const handleStationClick = (name) => {
    if (selectionMode === "origin") {
      setOrigin(name);
      if (name === destination) setDestination("");
      setSelectionMode("destination");
    } else {
      if (name === origin) return;
      setDestination(name);
      setSelectionMode("origin");
    }
  };

  const renderBranch = (stations, prefix) =>
    stations.map((s) => (
      <button
        key={`${prefix}-${s}`}
        className={`map-station${origin === s ? " is-origin" : ""}${destination === s ? " is-dest" : ""}`}
        onClick={() => handleStationClick(s)}
      >
        {s}
      </button>
    ));

  // ── HISTOGRAM ──────────────────────────────────────
  const renderHistogram = (bins, counts, p95) => {
    if (!bins || !counts) return null;
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

      <div className="mode-toggle">
        <button
          className={`mode-btn${mode === "leave-now" ? " active" : ""}`}
          onClick={() => { setMode("leave-now"); setResult(null); }}
        >Leave now</button>
        <button
          className={`mode-btn${mode === "arrive-by" ? " active" : ""}`}
          onClick={() => { setMode("arrive-by"); setResult(null); }}
        >Arrive by</button>
      </div>

      <div className="station-picker">
        <div className="picker-controls">
          <span className="picker-label">Select</span>
          <button
            className={`picker-tab origin-mode${selectionMode === "origin" ? " active" : ""}`}
            onClick={() => setSelectionMode("origin")}
          >origin</button>
          <span className="picker-arrow">→</span>
          <button
            className={`picker-tab dest-mode${selectionMode === "destination" ? " active" : ""}`}
            onClick={() => setSelectionMode("destination")}
          >destination</button>
        </div>
        {origin && destination && (
          <div className="picker-summary">{origin} → {destination}</div>
        )}
        <div className="map-cols">
          <div className="map-col">
            <div className="map-col-label">University</div>
            {renderBranch(UNIVERSITY_BRANCH, "univ")}
          </div>
          <div className="map-col">
            <div className="map-col-label">Yonge</div>
            {renderBranch(YONGE_BRANCH, "yonge")}
          </div>
        </div>
      </div>

      {mode === "arrive-by" && (
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
          <div className="field field-now">
            <label>&nbsp;</label>
            <button className="now-btn" onClick={resetToNow}>now</button>
          </div>
        </div>
      )}

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

      {result && !loading && result.type === "leave-now" && (
        <>
          <div className="depart-time">{fmt(result.depart_mins + result.mean_travel_min)}</div>
          <div className="depart-sub">
            Likely arrival · worst case {fmt(result.depart_mins + result.p95_travel_min)} (P95)
          </div>

          <table className="result-table">
            <tbody>
              <tr>
                <td>Route</td>
                <td>{origin} → {destination}</td>
              </tr>
              <tr>
                <td>Mean travel time</td>
                <td>{result.mean_travel_min} min</td>
              </tr>
              <tr>
                <td>P95 travel time</td>
                <td>{result.p95_travel_min} min</td>
              </tr>
              <tr>
                <td>Baseline (no delays)</td>
                <td>{result.baseline_min} min</td>
              </tr>
            </tbody>
          </table>

          {renderHistogram(result.histogram_bins, result.histogram_counts, result.p95_travel_min)}
        </>
      )}

      {result && !loading && result.type === "arrive-by" && (
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

          {renderHistogram(
            result.recommendation.histogram_bins,
            result.recommendation.histogram_counts,
            result.recommendation.p95_travel_min
          )}
        </>
      )}
      <p className="credit">
        By <a href="https://patrickmtaylor.com" target="_blank" rel="noopener noreferrer">Patrick Taylor</a> <em>(<a href="https://github.com/patrickt6/ttcmontecarlo" target="_blank" rel="noopener noreferrer">github</a>)</em>
      </p>
    </div>
  );
}
