/**
 * charts.js — Chart.js helpers, light blue theme.
 */
const Charts = (() => {
  const OCEAN = "#1A5F96", SKY = "#5BAFD6", GREEN = "#22C55E",
        AMBER = "#F59E0B", RED = "#EF4444",
        GRID  = "rgba(200,230,245,0.7)", TICK = "#9CA3AF";

  Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
  Chart.defaults.font.size   = 11;
  Chart.defaults.color       = TICK;
  Chart.defaults.plugins.legend.display = false;

  const tip = {
    backgroundColor: "#fff", titleColor: "#0B2040",
    bodyColor: "#374151", borderColor: "rgba(91,175,214,0.25)",
    borderWidth: 1, padding: 10, cornerRadius: 8,
    mode: "index", intersect: false
  };

  function ax(extra = {}) {
    return {
      grid: { color: GRID, drawBorder: false },
      ticks: { color: TICK, maxTicksLimit: 7, maxRotation: 0 },
      beginAtZero: true, ...extra
    };
  }

  function grad(ctx, hex, a1 = 0.18, a2 = 0) {
    const g = ctx.createLinearGradient(0, 0, 0, 200);
    g.addColorStop(0, hex + Math.round(a1*255).toString(16).padStart(2,"0"));
    g.addColorStop(1, hex + Math.round(a2*255).toString(16).padStart(2,"0"));
    return g;
  }

  const R = {};
  function kill(k) { if (R[k]) { R[k].destroy(); delete R[k]; } }

  function line(id, key, labels, data, color, yExtra = {}) {
    kill(key);
    const el = document.getElementById(id); if (!el) return;
    const ctx = el.getContext("2d");
    R[key] = new Chart(ctx, {
      type: "line",
      data: { labels, datasets: [{ data, borderColor: color, backgroundColor: grad(ctx, color), borderWidth: 2, pointRadius: 0, fill: true, tension: 0.4 }] },
      options: { responsive: true, maintainAspectRatio: false, animation: { duration: 500 }, plugins: { tooltip: tip }, scales: { x: ax(), y: ax(yExtra) } }
    });
  }

  function bar(id, key, labels, data, color, label) {
    kill(key);
    const el = document.getElementById(id); if (!el) return;
    const ctx = el.getContext("2d");
    R[key] = new Chart(ctx, {
      type: "bar",
      data: { labels, datasets: [{ label, data, backgroundColor: color + "88", borderColor: color, borderWidth: 1.5, borderRadius: 5, borderSkipped: false }] },
      options: { responsive: true, maintainAspectRatio: false, animation: { duration: 400 }, plugins: { legend: { display: true, labels: { color: "#374151" } }, tooltip: tip }, scales: { x: ax(), y: ax() } }
    });
  }

  return {
    miniFlow:    (l,d) => line("miniFlowChart",  "mf", l, d, OCEAN),
    miniTank:    (l,d) => line("miniTankChart",   "mt", l, d, SKY, { min:0, max:100 }),
    hourly:      (l,d) => bar ("hourlyChart",     "hr", l, d, SKY,   "Flow (L/min)"),
    daily:       (l,d) => bar ("dailyChart",      "dy", l, d, GREEN, "Daily Total"),
    tankTrend:   (l,d) => line("tankTrendChart",  "tt", l, d, AMBER, { min:0, max:100 }),
    costTrend:   (l,d) => line("costTrendChart",  "ct", l, d, RED),
  };
})();
