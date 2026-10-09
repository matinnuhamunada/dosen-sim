// Minimal SVG charts for the HUD (no charting dependency).

const NS = "http://www.w3.org/2000/svg";

export interface Series {
  name: string;
  color: string;
  values: (number | null)[]; // index = semester
  dashed?: boolean;
  band?: [number, number][]; // optional lower/upper per index (department IQR)
}

function el<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number>) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, String(v));
  return e;
}

export function lineChart(
  series: Series[],
  opts: { width: number; height: number; marker?: number; title: string; yFmt?: (v: number) => string },
): SVGSVGElement {
  const { width: w, height: h } = opts;
  const pad = { l: 34, r: 6, t: 16, b: 14 };
  const svg = el("svg", { width: w, height: h, viewBox: `0 0 ${w} ${h}`, class: "chart" });
  const all = series.flatMap((s) => [
    ...s.values.filter((v): v is number => v !== null && Number.isFinite(v)),
    ...(s.band ?? []).flat(),
  ]);
  const n = Math.max(1, ...series.map((s) => s.values.length));
  let lo = Math.min(0, ...all);
  let hi = Math.max(...all, lo + 1e-9);
  if (!Number.isFinite(hi)) hi = 1;
  if (!Number.isFinite(lo)) lo = 0;
  const x = (i: number) => pad.l + (i / Math.max(n - 1, 1)) * (w - pad.l - pad.r);
  const y = (v: number) => h - pad.b - ((v - lo) / (hi - lo || 1)) * (h - pad.t - pad.b);
  const fmt = opts.yFmt ?? ((v: number) => (Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(2)));
  const title = el("text", { x: pad.l, y: 11, class: "chart-title" });
  title.textContent = opts.title;
  svg.append(title);
  for (const v of [lo, hi]) {
    const tick = el("text", { x: pad.l - 4, y: y(v) + 3, class: "chart-tick", "text-anchor": "end" });
    tick.textContent = fmt(v);
    svg.append(tick, el("line", { x1: pad.l, x2: w - pad.r, y1: y(v), y2: y(v), class: "chart-grid" }));
  }
  for (const s of series) {
    if (s.band) {
      const up = s.band.map(([, u], i) => `${x(i)},${y(u)}`);
      const down = s.band.map(([l], i) => `${x(i)},${y(l)}`).reverse();
      svg.append(el("polygon", { points: [...up, ...down].join(" "), fill: s.color, opacity: 0.15 }));
    }
    let d = "";
    s.values.forEach((v, i) => {
      if (v === null || !Number.isFinite(v)) return;
      d += `${d && s.values[i - 1] !== null ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
    });
    if (d) {
      svg.append(el("path", {
        d, fill: "none", stroke: s.color, "stroke-width": 1.8,
        "stroke-dasharray": s.dashed ? "4 3" : "none",
      }));
    }
  }
  if (opts.marker !== undefined) {
    svg.append(el("line", {
      x1: x(opts.marker), x2: x(opts.marker), y1: pad.t, y2: h - pad.b, class: "chart-marker",
    }));
  }
  return svg;
}

export function stackedBars(
  rows: Record<string, number>[],
  keys: string[],
  colors: Record<string, string>,
  opts: { width: number; height: number; marker?: number; title: string; total: number },
): SVGSVGElement {
  const { width: w, height: h } = opts;
  const pad = { l: 4, r: 4, t: 16, b: 4 };
  const svg = el("svg", { width: w, height: h, viewBox: `0 0 ${w} ${h}`, class: "chart" });
  const title = el("text", { x: pad.l, y: 11, class: "chart-title" });
  title.textContent = opts.title;
  svg.append(title);
  const n = Math.max(rows.length, 1);
  const bw = (w - pad.l - pad.r) / n;
  rows.forEach((r, i) => {
    let acc = 0;
    for (const k of keys) {
      const v = r[k] ?? 0;
      const bh = (v / opts.total) * (h - pad.t - pad.b);
      const rect = el("rect", {
        x: pad.l + i * bw, y: h - pad.b - acc - bh, width: Math.max(bw - 0.5, 0.5), height: bh,
        fill: colors[k] ?? "#888", opacity: opts.marker === i ? 1 : 0.75,
      });
      const tip = el("title", {});
      tip.textContent = `t${i} ${k}: ${v.toFixed(1)} h/wk`;
      rect.append(tip);
      svg.append(rect);
      acc += bh;
    }
  });
  if (opts.marker !== undefined) {
    svg.append(el("rect", {
      x: pad.l + opts.marker * bw, y: pad.t, width: bw, height: h - pad.t - pad.b, class: "chart-cursor",
    }));
  }
  return svg;
}
