"use client";

import { useState } from "react";

export default function Home() {
  const [origin, setOrigin] = useState("Finch");
  const [destination, setDestination] = useState("Union");
  const [arriveHour, setArriveHour] = useState(9);
  const [arriveMinute, setArriveMinute] = useState(0);
  const [isWeekday, setIsWeekday] = useState(true);

  // Placeholder stations until API is wired up
  const stations = [
    "Finch", "North York Centre", "Sheppard-Yonge", "York Mills",
    "Lawrence", "Eglinton", "Davisville", "St Clair", "Summerhill",
    "Rosedale", "Bloor-Yonge", "Wellesley", "College", "TMU",
    "Queen", "King", "Union",
  ];

  return (
    <div className="page">
      <h1>TTC Monte Carlo Risk Simulator</h1>
      <p className="subtitle">
        Line 1 · 10,000 simulated journeys · historical delays 2014–2025
      </p>

      <div className="field">
        <label>Origin</label>
        <select value={origin} onChange={(e) => setOrigin(e.target.value)}>
          {stations.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div className="field">
        <label>Destination</label>
        <select value={destination} onChange={(e) => setDestination(e.target.value)}>
          {stations.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div className="field-row">
        <div className="field">
          <label>Arrive by (hour)</label>
          <select value={arriveHour} onChange={(e) => setArriveHour(parseInt(e.target.value))}>
            {Array.from({ length: 24 }, (_, i) => (
              <option key={i} value={i}>{i}:00</option>
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

      <p className="status">Results will appear here once the API is connected.</p>
    </div>
  );
}
