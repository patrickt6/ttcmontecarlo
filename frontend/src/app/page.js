"use client";

import { useEffect, useMemo, useState } from "react";
import { loadModel, route, simulate, summarize, histogram, latestDeparture } from "./sim";

const YONGE_END = "Union";
const pad = (n) => String(n).padStart(2, "0");
const fmt = (mins) => {
  const m = ((Math.round(mins) % 1440) + 1440) % 1440;
  const h = Math.floor(m / 60);
  return `${h % 12 || 12}:${pad(m % 60)} ${h < 12 ? "am" : "pm"}`;
};
const nowMins = () => {
  const d = new Date();
  return d.getHours() * 60 + d.getMinutes();
};
const isWeekdayToday = () => {
  const day = new Date().getDay();
  return day !== 0 && day !== 6;
};
const store = {
  get(k, fallback) {
    try {
      const v = localStorage.getItem(k);
      return v === null ? fallback : JSON.parse(v);
    } catch {
      return fallback;
    }
  },
  set(k, v) {
    try {
      localStorage.setItem(k, JSON.stringify(v));
    } catch {}
  },
};

export default function Home() {
  const [model, setModel] = useState(null);
  const [loadError, setLoadError] = useState(false);

  const [origin, setOrigin] = useState("St Clair West");
  const [destination, setDestination] = useState("Union");
  const [mode, setMode] = useState("now");
  const [arriveBy, setArriveBy] = useState("09:00");
  const [weekday, setWeekday] = useState(true);
  const [confidence, setConfidence] = useState(0.9);
  const [clock, setClock] = useState(0);

  useEffect(() => {
    loadModel().then(setModel).catch(() => setLoadError(true));
    const saved = store.get("ttc-route", null);
    if (saved?.origin) setOrigin(saved.origin);
    if (saved?.destination) setDestination(saved.destination);
    setWeekday(isWeekdayToday());
    setClock(nowMins());
    const t = setInterval(() => setClock(nowMins()), 30000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    store.set("ttc-route", { origin, destination });
  }, [origin, destination]);

  const result = useMemo(() => {
    if (!model || origin === destination) return null;
    const stops = route(model, origin, destination);
    const base = (stops.length - 1) * model.segment_min;

    if (mode === "now") {
      const times = simulate(model, stops, Math.floor(clock / 60), weekday);
      return { kind: "now", stops, base, times, s: summarize(times), depart: clock };
    }
    const [h, m] = arriveBy.split(":").map(Number);
    const deadline = h * 60 + m;
    const pick = latestDeparture(model, stops, deadline, weekday, confidence);
    return pick ? { kind: "by", stops, base, deadline, ...pick, s: summarize(pick.times) } : { kind: "none", stops, base };
  }, [model, origin, destination, mode, arriveBy, weekday, confidence, clock]);

  const swap = () => {
    setOrigin(destination);
    setDestination(origin);
  };

  const stations = model?.stations ?? [];
  const yonge = stations.slice(0, stations.indexOf(YONGE_END) + 1);
  const university = stations.slice(stations.indexOf(YONGE_END) + 1);
  const Options = () => (
    <>
      <optgroup label="Yonge branch">{yonge.map((s) => <option key={s}>{s}</option>)}</optgroup>
      <optgroup label="University branch">{university.map((s) => <option key={s}>{s}</option>)}</optgroup>
    </>
  );

  return (
    <main className="page">
      <header className="top">
        <span className="bullet">1</span>
        <div>
          <h1>Will I make it on Line 1?</h1>
          <p className="sub">Your trip, run 10,000 times against real TTC delay records.</p>
        </div>
      </header>

      <section className="card form">
        <div className="route">
          <label className="field">
            <span>From</span>
            <select value={origin} onChange={(e) => setOrigin(e.target.value)} disabled={!model}>
              {model ? <Options /> : <option>{origin}</option>}
            </select>
          </label>
          <button className="swap" onClick={swap} aria-label="Swap stations">&#8645;</button>
          <label className="field">
            <span>To</span>
            <select value={destination} onChange={(e) => setDestination(e.target.value)} disabled={!model}>
              {model ? <Options /> : <option>{destination}</option>}
            </select>
          </label>
        </div>

        <div className="seg" role="tablist">
          <button className={mode === "now" ? "on" : ""} onClick={() => setMode("now")}>Leave now</button>
          <button className={mode === "by" ? "on" : ""} onClick={() => setMode("by")}>Arrive by</button>
        </div>

        {mode === "by" && (
          <div className="row">
            <label className="field grow">
              <span>Need to be there by</span>
              <input type="time" value={arriveBy} onChange={(e) => e.target.value && setArriveBy(e.target.value)} />
            </label>
            <label className="field">
              <span>How sure</span>
              <select value={confidence} onChange={(e) => setConfidence(Number(e.target.value))}>
                <option value={0.8}>80%</option>
                <option value={0.9}>90%</option>
                <option value={0.95}>95%</option>
              </select>
            </label>
          </div>
        )}

        <div className="chips">
          <button className={weekday ? "on" : ""} onClick={() => setWeekday(true)}>Weekday</button>
          <button className={!weekday ? "on" : ""} onClick={() => setWeekday(false)}>Weekend</button>
        </div>
      </section>

      {loadError && <p className="card error">Could not load the delay data. Refresh to try again.</p>}
      {!model && !loadError && <p className="card muted">Loading delay records…</p>}
      {model && origin === destination && <p className="card muted">Pick two different stations.</p>}

      {result?.kind === "now" && (
        <section className="card result">
          <p className="eyebrow">Leaving at {fmt(result.depart)}</p>
          <p className="big">{fmt(result.depart + result.s.median)}</p>
          <p className="lead">is your most likely arrival. Plan for <b>{fmt(result.depart + result.s.p95)}</b> to be safe 19 times out of 20.</p>
          <Chart times={result.times} cut={result.s.p95} cutLabel="95% of trips done" />
          <Stats r={result} />
        </section>
      )}

      {result?.kind === "by" && (
        <section className="card result">
          <p className="eyebrow">To arrive by {fmt(result.deadline)}, {Math.round(confidence * 100)}% sure</p>
          <p className="big">Leave by {fmt(result.depart)}</p>
          <p className="lead">
            {result.depart >= clock && result.depart - clock < 180
              ? `That's in ${result.depart - clock} min. `
              : ""}
            Leaving then gets you there on time in <b>{Math.round(result.prob * 100)}%</b> of simulated trips.
          </p>
          <Chart times={result.times} cut={result.deadline - result.depart} cutLabel="your deadline" />
          <Stats r={result} />
        </section>
      )}

      {result?.kind === "none" && (
        <p className="card error">No departure in the 3 hours before that time is safe enough. Try a lower level.</p>
      )}

      <footer className="foot">
        <p>
          {model ? `${model.rows.toLocaleString()} delay records, ${model.first_date.slice(0, 4)} to ${model.last_date.slice(0, 4)}` : "TTC open data"}.
          Each run walks the stations on your trip, adds a delay at each one with the chance seen in the records for that
          station, hour and day type, and assumes {model?.segment_min ?? 2} minutes between stops. It is an estimate from
          past delays, not a live service alert.
        </p>
        <p>
          By <a href="https://patrickmtaylor.com">Patrick Taylor</a> · <a href="https://github.com/patrickt6/ttcmontecarlo">source</a>
        </p>
      </footer>
    </main>
  );
}

function Chart({ times, cut, cutLabel }) {
  const { bins, lo, hi } = histogram(times, 36);
  const max = Math.max(...bins);
  const x = Math.min(Math.max((cut - lo) / (hi - lo || 1), 0), 1) * 100;
  return (
    <figure className="chart">
      <div className="bars">
        {bins.map((c, i) => (
          <i
            key={i}
            className={lo + ((i + 0.5) * (hi - lo)) / bins.length > cut ? "late" : ""}
            style={{ height: `${Math.max((c / max) * 100, c ? 3 : 0)}%` }}
          />
        ))}
        <span className="cut" style={{ left: `${x}%` }}><em>{cutLabel}</em></span>
      </div>
      <figcaption>
        <span>{Math.round(lo)} min</span>
        <span>trip length</span>
        <span>{Math.round(hi)} min</span>
      </figcaption>
    </figure>
  );
}

function Stats({ r }) {
  return (
    <dl className="stats">
      <div><dt>Stops</dt><dd>{r.stops.length - 1}</dd></div>
      <div><dt>No delays</dt><dd>{r.base} min</dd></div>
      <div><dt>Typical</dt><dd>{Math.round(r.s.median)} min</dd></div>
      <div><dt>Bad day (1 in 20)</dt><dd>{Math.round(r.s.p95)} min</dd></div>
    </dl>
  );
}
