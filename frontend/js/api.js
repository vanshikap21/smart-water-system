/**
 * api.js — fetch wrapper for all backend endpoints.
 */
const Api = (() => {
  const BASE = window.location.origin;

  async function req(method, path, body) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(BASE + path, opts);
    if (!res.ok) {
      const e = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(e.error || `HTTP ${res.status}`);
    }
    return res.json();
  }

  return {
    getLiveData:          () => req("GET",  "/api/live-data"),
    getAnalytics:         () => req("GET",  "/api/analytics"),
    getMonitoring: (n=50) => req("GET",  `/api/monitoring?limit=${n}`),
    getLeakStatus:        () => req("GET",  "/api/leak-status"),
    getLeakHistory:(n=15) => req("GET",  `/api/leak-history?limit=${n}`),
    getCost:              () => req("GET",  "/api/cost"),
    getConservation:      () => req("GET",  "/api/conservation-score"),
    generateInsight:      () => req("POST", "/api/generate-insight"),
    generateReport:       () => req("POST", "/api/generate-report"),
    calcSavings: (pct)       => req("POST", "/api/calculate-savings", { reduction_percent: pct }),
  };
})();
