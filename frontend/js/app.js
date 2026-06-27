/**
 * app.js — SmartTap main controller.
 * Handles: landing ↔ dashboard routing, demo mode,
 * page navigation, data loading, all UI updates.
 */
(() => {
  "use strict";

  /* ═══════════════════════════════════════
     DEMO DATA — realistic hardcoded values
  ═══════════════════════════════════════ */
  const DEMO = {
    live: {
      timestamp: new Date().toISOString().slice(0,19).replace("T"," "),
      flow_rate: 12.4, tank_level: 78.0,
      leak: { status:"No Leak", confidence:96.2, reason:"Normal usage pattern. Flow 12.4 L/min, tank at 78%. No anomalies detected (confidence 96.2%)." },
      cost: { estimated_cost:0.00621, category:"Low", reason:"Standard pricing.", is_peak_hour:false },
      conservation: { score:86, category:"Excellent" }
    },
    analytics: {
      hourly_consumption: Array.from({length:24},(_,i)=>({ hour:String(i).padStart(2,"0"), total_flow:+(Math.sin(i/3.5)*4+11+Math.random()*3).toFixed(2) })),
      daily_consumption:  ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map(d=>({ date:d, total_flow:+(Math.random()*40+60).toFixed(2) })),
      tank_level_trend:   Array.from({length:30},(_,i)=>({ timestamp:new Date(Date.now()-i*5*60000).toISOString().slice(0,19).replace("T"," "), tank_level:+(78+Math.sin(i/5)*7+(Math.random()-.5)*3).toFixed(1) })).reverse(),
      cost_trend:         Array.from({length:30},(_,i)=>({ timestamp:new Date(Date.now()-i*5*60000).toISOString().slice(0,19).replace("T"," "), estimated_cost:+(0.004+Math.random()*0.005).toFixed(5) })).reverse()
    },
    monitoring: Array.from({length:20},(_,i)=>({
      id:20-i,
      timestamp:new Date(Date.now()-i*5000).toISOString().slice(0,19).replace("T"," "),
      flow_rate:+(8+Math.random()*10).toFixed(2),
      tank_level:+(76+(Math.random()-.5)*10).toFixed(1)
    })),
    leakStatus: { status:"No Leak", confidence:96.2, reason:"Normal usage pattern. Flow 12.4 L/min, tank at 78%. No anomalies detected.", flow_rate:12.4, tank_level:78, timestamp:new Date().toISOString().slice(0,19).replace("T"," ") },
    leakHistory: Array.from({length:10},(_,i)=>({ id:10-i, timestamp:new Date(Date.now()-i*3600000).toISOString().slice(0,19).replace("T"," "), status:i===3?"Leak":"No Leak", confidence:i===3?88.5:+(92+Math.random()*7).toFixed(1) })),
    savings: (p) => { const c=0.00621, r=+(c*(1-p/100)).toFixed(5); return { current_cost:c, projected_cost:r, savings:+(c-r).toFixed(5), annual_savings:+((c-r)*60*24*365).toFixed(2) }; },
    insight: `📊 Usage Analysis\nYour current flow rate of 12.4 L/min is within normal range for this time of day. Tank level at 78% is healthy — no immediate refill required.\n\n💡 Water-Saving Recommendations\n• Schedule heavy usage outside the 6–9 AM and 5–9 PM peak windows to reduce costs by up to 33%.\n• Check bathroom fixtures for slow drips — a 1 L/hr drip wastes ~730 litres/month.\n• Consider installing aerators on kitchen taps to reduce flow by 30%.\n• Your Conservation Score of 86 (Excellent) is great — maintain it!\n\n⚠️ Risk Assessment\nLOW RISK — No anomalies detected. Tank is stable and no leak signature found.\n\n✅ Priority Actions\n1. No immediate action required.\n2. Review your cost trend — usage spiked yesterday at 19:00.\n3. Set a daily conservation goal of 90+ for consistent Excellent rating.`,
    report: `# 📋 SmartTap Daily Water Report\n\n## 1. Executive Summary\nYesterday's water usage was within normal parameters with an average flow of 11.8 L/min across 24 hours. No sustained leaks were detected. Conservation Score: 86 — Excellent.\n\n## 2. Usage Patterns\n- Peak hour: 08:00 (morning routine)\n- Off-peak avg: 8.2 L/min  |  Peak avg: 18.6 L/min\n- Estimated total volume: ~17,000 litres\n\n## 3. Leak & Safety Analysis\n0 leak incidents in the last 24 hours. The ML classifier flagged 1 momentary spike at 21:14 — assessed as a toilet flush, not a structural leak.\n\n## 4. Cost Assessment\nTotal estimated spend: ₹4.32 for the day. Peak-hour usage accounted for 38% of daily cost despite representing only 18% of time.\n\n## 5. Recommendations for Tomorrow\n1. Shift 1 laundry cycle from 18:00 to 14:00 → save ~₹0.40/day.\n2. Tank at 78% — no refill needed for 48+ hours.\n3. Enable scheduled conservation alerts for the 5–9 PM window.\n\n## 6. Conservation Rating\n🏆 EXCELLENT — Score: 86/100\nYou're in the top 15% of monitored buildings.`
  };

  /* ═══════════════════════════════════════
     STATE
  ═══════════════════════════════════════ */
  let demo       = false;
  let curPage    = "overview";
  let autoOn     = true;
  let timer      = null;
  const TICK_MS  = 5000;

  /* ═══════════════════════════════════════
     UTILS
  ═══════════════════════════════════════ */
  const $  = id => document.getElementById(id);
  const qs = s  => document.querySelector(s);
  const qsa= s  => document.querySelectorAll(s);

  const loader = $("gLoader");
  const showLoad = () => loader.classList.add("on");
  const hideLoad = () => loader.classList.remove("on");

  function fmtTime(ts) {
    if (!ts) return "—";
    try { return new Date((ts.includes("T")?ts:ts+"Z")).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit",second:"2-digit"}); }
    catch { return ts.slice(11,19)||ts; }
  }

  function pill(text, cls) { return `<span class="spill ${cls}">${text}</span>`; }

  function stampTime() {
    $("lastUpdate").textContent = "Updated " + new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit",second:"2-digit"});
  }

  function setStatus(s) {
    const dot = $("statusDot"), lbl = $("statusLabel");
    dot.className = "status-dot " + s;
    lbl.textContent = s==="live" ? "Live" : s==="demo" ? "Demo Mode" : "Offline";
  }

  async function fetch_data(apiFn, fallback) {
    if (demo) { await new Promise(r=>setTimeout(r,220)); return typeof fallback==="function"?fallback():fallback; }
    return apiFn();
  }

  /* ═══════════════════════════════════════
     LANDING  ↔  DASHBOARD ROUTING
  ═══════════════════════════════════════ */
  function showLanding() {
    $("landingPage").style.display = "block";
    $("appPage").style.display     = "none";
    stopTick();
    // Restart landing animations by cloning hero content
    initLandingAnimations();
  }

  function showApp(demoMode=false) {
    $("landingPage").style.display = "none";
    $("appPage").style.display     = "block";
    setDemoMode(demoMode);
    navigate("overview");
    startTick();
  }

  function setDemoMode(on) {
    demo = on;
    $("demoToggle").checked        = on;
    $("demoBanner").style.display  = on ? "flex" : "none";
    setStatus(on ? "demo" : "offline");
  }

  /* ═══════════════════════════════════════
     PAGE NAVIGATION
  ═══════════════════════════════════════ */
  const PAGE_TITLES = { overview:"Overview", monitoring:"Live Monitoring", analytics:"Analytics", ml:"ML Insights", advisor:"AI Advisor" };

  function navigate(page) {
    qsa(".page").forEach(p=>p.classList.remove("active"));
    qsa(".sb-link").forEach(n=>n.classList.remove("active"));
    const sec = $("page-"+page);
    const lnk = qs(`.sb-link[data-page="${page}"]`);
    if (sec) sec.classList.add("active");
    if (lnk) lnk.classList.add("active");
    curPage = page;
    $("pageTitle").textContent = PAGE_TITLES[page]||page;
    $("sidebar").classList.remove("open");
    loadPage(page);
  }

  async function loadPage(page) {
    try {
      if (page==="overview")   await loadOverview();
      if (page==="monitoring") await loadMonitoring();
      if (page==="analytics")  await loadAnalytics();
      if (page==="ml")         await loadML();
      if (!demo) setStatus("live");
    } catch(e) {
      console.error(e);
      if (!demo) setStatus("offline");
    }
    stampTime();
  }

  /* ═══════════════════════════════════════
     OVERVIEW
  ═══════════════════════════════════════ */
  async function loadOverview() {
    const d = await fetch_data(()=>Api.getLiveData(), DEMO.live);
    const flow = +d.flow_rate, tank = +d.tank_level, isLeak = d.leak?.status==="Leak";

    // Flow
    $("kpiFlow").textContent = flow.toFixed(2);
    const fb = $("flowBadge");
    if (flow>20){ fb.textContent="High";    fb.className="kc-badge red"; }
    else if(flow>10){ fb.textContent="Moderate"; fb.className="kc-badge amber";}
    else        { fb.textContent="Normal";  fb.className="kc-badge"; }
    $("flowBar").style.width = Math.min(flow/30*100,100)+"%";

    // Tank
    $("kpiTank").textContent = tank.toFixed(1);
    const tb = $("tankBadge");
    if(tank<20){ tb.textContent="Critical"; tb.className="kc-badge red"; }
    else if(tank<40){ tb.textContent="Low"; tb.className="kc-badge amber"; }
    else { tb.textContent="Good"; tb.className="kc-badge green"; }
    $("tankBar").style.width = tank+"%";

    // Leak
    $("kpiLeak").textContent = d.leak?.status||"—";
    $("kpiLeak").style.color = isLeak?"var(--red)":"var(--green)";
    $("kpiLeakConf").textContent = d.leak?.confidence ? `confidence ${d.leak.confidence}%` : "—";
    $("leakBar").style.background = isLeak ? "var(--red)" : "var(--green)";

    // Cost
    $("kpiCost").textContent = d.cost?.estimated_cost?.toFixed(5)||"—";
    const cb = $("costBadge"), cat = d.cost?.category||"—";
    cb.textContent = cat;
    cb.className = cat==="Critical"||cat==="High" ? "kc-badge red" : cat==="Moderate" ? "kc-badge amber" : "kc-badge";
    $("costReason").textContent = d.cost?.reason||"—";

    // Score ring (circumference = 2π×30 ≈ 188)
    const sc = d.conservation?.score||0;
    $("scoreNum").textContent = sc;
    $("scoreCat").textContent = d.conservation?.category||"—";
    const rp = $("srProg");
    rp.style.stroke = sc>=80?"var(--green)":sc>=60?"var(--ocean)":sc>=40?"var(--amber)":"var(--red)";
    rp.style.strokeDashoffset = 188-(sc/100)*188;

    // Mini charts
    const an = await fetch_data(()=>Api.getAnalytics(), DEMO.analytics);
    Charts.miniFlow(an.hourly_consumption.map(r=>r.hour+":00"), an.hourly_consumption.map(r=>r.total_flow));
    Charts.miniTank(an.tank_level_trend.slice(-20).map(r=>fmtTime(r.timestamp)), an.tank_level_trend.slice(-20).map(r=>r.tank_level));
  }

  /* ═══════════════════════════════════════
     MONITORING
  ═══════════════════════════════════════ */
  async function loadMonitoring() {
    const rows = await fetch_data(()=>Api.getMonitoring(50), DEMO.monitoring);
    const tb = $("monBody");
    if(!rows.length){ tb.innerHTML=`<tr><td colspan="5" class="td-empty">No readings yet.</td></tr>`; return; }
    tb.innerHTML = rows.map((r,i)=>{
      const f=+r.flow_rate;
      const p = f>20?pill("High","sp-red"):f>10?pill("Moderate","sp-amber"):pill("Normal","sp-green");
      return `<tr>
        <td style="color:var(--text-muted);font-size:.78rem">${i+1}</td>
        <td style="font-family:'Courier New',monospace;font-size:.8rem;color:var(--text-sub)">${fmtTime(r.timestamp)}</td>
        <td style="font-weight:600;font-variant-numeric:tabular-nums">${f.toFixed(2)}</td>
        <td style="font-weight:600;font-variant-numeric:tabular-nums">${(+r.tank_level).toFixed(1)}</td>
        <td>${p}</td>
      </tr>`;
    }).join("");
  }

  /* ═══════════════════════════════════════
     ANALYTICS
  ═══════════════════════════════════════ */
  async function loadAnalytics() {
    const an = await fetch_data(()=>Api.getAnalytics(), DEMO.analytics);
    Charts.hourly(   an.hourly_consumption.map(r=>r.hour+":00"), an.hourly_consumption.map(r=>r.total_flow));
    Charts.daily(    an.daily_consumption.map(r=>r.date),        an.daily_consumption.map(r=>r.total_flow));
    Charts.tankTrend(an.tank_level_trend.map(r=>fmtTime(r.timestamp)), an.tank_level_trend.map(r=>r.tank_level));
    Charts.costTrend(an.cost_trend.map(r=>fmtTime(r.timestamp)), an.cost_trend.map(r=>r.estimated_cost));
  }

  /* ═══════════════════════════════════════
     ML INSIGHTS
  ═══════════════════════════════════════ */
  async function loadML() { await loadLeakHistory(); }

  async function runPred() {
    const btn=$("runPredBtn"); btn.disabled=true; btn.textContent="Analysing…";
    try {
      const r = await fetch_data(()=>Api.getLeakStatus(), DEMO.leakStatus);
      const isLeak = r.status==="Leak";
      $("mlResult").innerHTML = `
        <div class="ml-chip ${isLeak?"leak":"ok"}">${r.status}</div>
        <div class="ml-conf">
          <span class="ml-conf-lbl">Confidence</span>
          <div class="ml-conf-track"><div class="ml-conf-fill" style="width:${r.confidence}%"></div></div>
          <span class="ml-conf-pct">${r.confidence}%</span>
        </div>
        <div class="ml-reason">${r.reason}</div>
        <div class="ml-meta">Flow: <strong>${r.flow_rate} L/min</strong> &nbsp;|&nbsp; Tank: <strong>${r.tank_level}%</strong> &nbsp;|&nbsp; ${fmtTime(r.timestamp)}</div>
      `;
      await loadLeakHistory();
    } catch(e) { $("mlResult").innerHTML=`<div class="ml-empty" style="color:var(--red)">Error: ${e.message}</div>`; }
    finally { btn.disabled=false; btn.textContent="Run Prediction"; }
  }

  async function loadLeakHistory() {
    const logs = await fetch_data(()=>Api.getLeakHistory(15), DEMO.leakHistory);
    const tb   = $("leakLogBody");
    if(!logs.length){ tb.innerHTML=`<tr><td colspan="3" class="td-empty">No logs.</td></tr>`; return; }
    tb.innerHTML = logs.map(r=>`<tr>
      <td style="font-family:'Courier New',monospace;font-size:.78rem">${fmtTime(r.timestamp)}</td>
      <td>${r.status==="Leak"?pill("Leak","sp-red"):pill("No Leak","sp-green")}</td>
      <td style="font-variant-numeric:tabular-nums;font-weight:600">${r.confidence}%</td>
    </tr>`).join("");
  }

  /* ═══════════════════════════════════════
     AI ADVISOR
  ═══════════════════════════════════════ */
  async function genInsight() {
    const btn=$("insightBtn"); btn.disabled=true; btn.textContent="Generating…";
    $("insightOut").innerHTML=`<span class="ai-ph">⏳ Asking Gemini AI…</span>`;
    try {
      if(demo){ await new Promise(r=>setTimeout(r,1100)); $("insightOut").textContent=DEMO.insight; }
      else { const r=await Api.generateInsight(); $("insightOut").textContent=r.success?r.insight:"⚠ "+r.insight; }
    } catch(e){ $("insightOut").textContent="Error: "+e.message; }
    finally { btn.disabled=false; btn.textContent="Generate Insight"; }
  }

  async function genReport() {
    const btn=$("reportBtn"); btn.disabled=true; btn.textContent="Generating…";
    $("reportOut").innerHTML=`<span class="ai-ph">⏳ Building daily report…</span>`;
    try {
      if(demo){ await new Promise(r=>setTimeout(r,1300)); $("reportOut").textContent=DEMO.report; }
      else { const r=await Api.generateReport(); $("reportOut").textContent=r.success?r.report:"⚠ "+r.report; }
    } catch(e){ $("reportOut").textContent="Error: "+e.message; }
    finally { btn.disabled=false; btn.textContent="Generate Daily Report"; }
  }

  async function calcSav(pct) {
    try {
      const r = await fetch_data(()=>Api.calcSavings(pct), ()=>DEMO.savings(pct));
      $("savResult").style.display="flex";
      $("savCurrent").textContent ="₹"+r.current_cost.toFixed(5);
      $("savProj").textContent    ="₹"+r.projected_cost.toFixed(5);
      $("savAnnual").textContent  ="₹"+r.annual_savings.toLocaleString("en-IN");
    } catch(e){ alert("Error: "+e.message); }
  }

  /* ═══════════════════════════════════════
     AUTO-REFRESH
  ═══════════════════════════════════════ */
  function startTick() { stopTick(); timer=setInterval(()=>{ if(autoOn)loadPage(curPage); },TICK_MS); }
  function stopTick()  { if(timer){ clearInterval(timer); timer=null; } }

  /* ═══════════════════════════════════════
     LANDING ANIMATIONS
  ═══════════════════════════════════════ */
  function initLandingAnimations() {
    // Count-up for hero card values
    document.querySelectorAll(".lgc-val[data-target]").forEach(el => {
      el._counted = false;
    });
    // Trigger after a short delay
    setTimeout(() => {
      document.querySelectorAll(".lgc-val[data-target]").forEach(el => countUp(el));
    }, 700);

    // Scroll-reveal observer
    const io = new IntersectionObserver(entries => {
      entries.forEach(e => { if(e.isIntersecting){ e.target.classList.add("in"); io.unobserve(e.target); } });
    }, { threshold: 0.12, rootMargin: "0px 0px -30px 0px" });
    document.querySelectorAll(".reveal").forEach(el => { el.classList.remove("in"); io.observe(el); });

    // Count-up for stats bar
    const co = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if(e.isIntersecting && !e.target._counted){ e.target._counted=true; countUp(e.target); co.unobserve(e.target); }
      });
    }, { threshold: 0.5 });
    document.querySelectorAll(".count-anim").forEach(el => co.observe(el));

    // Live time display
    setInterval(() => {
      const el = document.getElementById("heroTime");
      if(el) el.textContent = new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit",second:"2-digit"});
    }, 1000);
  }

  function countUp(el) {
    const target = parseFloat(el.dataset.target);
    const dec    = parseInt(el.dataset.dec ?? "0");
    const dur    = 1400;
    const start  = performance.now();
    const tick = now => {
      const p = Math.min((now-start)/dur, 1);
      const e = 1-Math.pow(1-p,3);
      el.textContent = (target*e).toFixed(dec);
      if(p<1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  /* ═══════════════════════════════════════
     EVENT LISTENERS
  ═══════════════════════════════════════ */
  // Landing → app
  ["landLaunchBtn","heroLaunchBtn","ctaLaunchBtn"].forEach(id => $(`${id}`)?.addEventListener("click",()=>showApp(false)));
  $("heroDemoBtn")?.addEventListener("click",()=>showApp(true));

  // Back to landing
  $("backToLanding")?.addEventListener("click",()=>{ stopTick(); showLanding(); });

  // Demo toggle
  $("demoToggle")?.addEventListener("change",()=>{ setDemoMode($("demoToggle").checked); loadPage(curPage); });
  $("exitDemoBtn")?.addEventListener("click",()=>{ setDemoMode(false); loadPage(curPage); });

  // Sidebar nav
  qsa(".sb-link").forEach(el=>el.addEventListener("click",e=>{ e.preventDefault(); navigate(el.dataset.page); }));

  // Mobile menu
  $("menuBtn")?.addEventListener("click",()=>$("sidebar").classList.toggle("open"));

  // Refresh
  $("refreshBtn")?.addEventListener("click",()=>loadPage(curPage));

  // Auto-refresh toggle
  $("autoRefresh")?.addEventListener("change",e=>{ autoOn=e.target.checked; });

  // ML
  $("runPredBtn")?.addEventListener("click",runPred);

  // AI
  $("insightBtn")?.addEventListener("click",genInsight);
  $("reportBtn")?.addEventListener("click",genReport);

  // Savings
  qsa(".sav-btn").forEach(btn=>btn.addEventListener("click",()=>calcSav(+btn.dataset.r)));
  $("customSavBtn")?.addEventListener("click",()=>{ const v=parseFloat($("customPct").value); if(!v||v<1||v>99)return alert("Enter 1–99"); calcSav(v); });

  /* ═══════════════════════════════════════
     INIT
  ═══════════════════════════════════════ */
  showLanding();

})();
