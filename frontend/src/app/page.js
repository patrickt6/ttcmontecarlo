"use client";

import { useState, useEffect } from "react";

export default function Home() {
  const [stations, setStations] = useState([]);
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [arriveHour, setArriveHour] = useState(9);
  const [arriveMinute, setArriveMinute] = useState(0);
  const [isWeekday, setIsWeekday] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
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

      {error && <p className="error">{error}</p>}
      {!error && stations.length === 0 && <p className="status">Loading stations...</p>}
      {stations.length > 0 && <p className="status">Select a route above to run a simulation.</p>}
    </div>
  );
}
