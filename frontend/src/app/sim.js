// Monte Carlo trip simulator, run in the browser.
// Same model as src/simulation/monte_carlo.py: for every station on the route,
// a delay happens with probability p (from the records for that station, hour
// and day type), and its size is drawn from the delays seen there.
// The distributions come from public/distributions.json, built by
// src/simulation/export_distributions.py.

const RUNS = 10000;

export async function loadModel() {
  const resp = await fetch("/distributions.json");
  if (!resp.ok) throw new Error("distributions.json not found");
  const m = await resp.json();
  // Precompute a cumulative table per group so each draw is a binary search.
  for (const key of Object.keys(m.d)) {
    const [p, pairs] = m.d[key];
    const vals = new Float64Array(pairs.length);
    const cum = new Float64Array(pairs.length);
    let total = 0;
    pairs.forEach(([v, c], i) => {
      total += c;
      vals[i] = v;
      cum[i] = total;
    });
    m.d[key] = { p, vals, cum, total };
  }
  return m;
}

export function route(model, origin, destination) {
  const s = model.stations;
  const a = s.indexOf(origin);
  const b = s.indexOf(destination);
  return a <= b ? s.slice(a, b + 1) : s.slice(b, a + 1).reverse();
}

function draw({ vals, cum, total }) {
  const r = Math.random() * total;
  let lo = 0;
  let hi = cum.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (cum[mid] > r) hi = mid;
    else lo = mid + 1;
  }
  return vals[lo];
}

export function simulate(model, stops, hour, weekday) {
  const base = (stops.length - 1) * model.segment_min;
  const out = new Float64Array(RUNS).fill(base);
  const h = ((hour % 24) + 24) % 24;
  for (const station of stops) {
    const g = model.d[`${station}|${h}|${weekday ? 1 : 0}`];
    if (!g) continue;
    for (let i = 0; i < RUNS; i++) {
      if (Math.random() < g.p) out[i] += draw(g);
    }
  }
  return out.sort();
}

const pct = (sorted, q) => sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))];

export function summarize(sorted) {
  return { median: pct(sorted, 0.5), p95: pct(sorted, 0.95), worst: sorted[sorted.length - 1] };
}

// Share of runs that finish within `limit` minutes (sorted input).
function within(sorted, limit) {
  let lo = 0;
  let hi = sorted.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (sorted[mid] <= limit) lo = mid + 1;
    else hi = mid;
  }
  return lo / sorted.length;
}

// Latest departure, in 1-minute steps over the 3 hours before the deadline,
// that arrives on time with at least `confidence`. Each hour is simulated once.
export function latestDeparture(model, stops, deadline, weekday, confidence) {
  const cache = new Map();
  const timesAt = (depart) => {
    const h = Math.floor((((depart % 1440) + 1440) % 1440) / 60);
    if (!cache.has(h)) cache.set(h, simulate(model, stops, h, weekday));
    return cache.get(h);
  };
  for (let depart = deadline; depart >= deadline - 180; depart--) {
    const times = timesAt(depart);
    const prob = within(times, deadline - depart);
    if (prob >= confidence) return { depart, prob, times };
  }
  return null;
}

export function histogram(sorted, n) {
  // Clip the long right tail at the 99th percentile so the shape stays readable.
  const lo = sorted[0];
  const hi = Math.max(pct(sorted, 0.99), lo + 1);
  const bins = new Array(n).fill(0);
  for (const t of sorted) {
    if (t > hi) {
      bins[n - 1]++;
      continue;
    }
    bins[Math.min(n - 1, Math.floor(((t - lo) / (hi - lo)) * n))]++;
  }
  return { bins, lo, hi };
}
