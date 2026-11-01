import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity, BatteryCharging, Bolt, CarFront, ChevronDown, CircleHelp,
  Download, Gauge, Pause, Play, RotateCcw, Settings2, Sun, Timer,
  Waves, Zap, SlidersHorizontal, Cpu, Radio, ChartNoAxesCombined
} from 'lucide-react';
import { DEFAULTS, parseTrackCsv, simulateLap } from './simulation';
import './index.css';

const PRESETS = {
  baseline: { label: 'Baseline', patch: {} },
  sprint: { label: 'Sprint setup', patch: { vehicle_mass: 285, motor_peak_power_kw: 15, motor_peak_torque_nm: 82, friction_coefficient: 1.28, drag_coefficient: 0.19 } },
  endurance: { label: 'Endurance', patch: { vehicle_mass: 310, motor_peak_power_kw: 9, motor_peak_torque_nm: 65, friction_coefficient: 1.05, solar_irradiance_wm2: 950, initial_soc_pct: 98 } },
  wet: { label: 'Low-grip / wet', patch: { friction_coefficient: 0.72, drag_coefficient: 0.22, rolling_resistance_coeff: 0.009 } }
};

const PARAMS = [
  { key: 'vehicle_mass', label: 'Vehicle + driver mass', unit: 'kg', min: 180, max: 600, step: 5 },
  { key: 'drag_coefficient', label: 'Drag coefficient (Cd)', unit: '', min: 0.10, max: 0.50, step: 0.01 },
  { key: 'frontal_area', label: 'Frontal area', unit: 'm²', min: 0.7, max: 2.5, step: 0.05 },
  { key: 'rolling_resistance_coeff', label: 'Rolling resistance (Crr)', unit: '', min: 0.002, max: 0.03, step: 0.001 },
  { key: 'friction_coefficient', label: 'Tyre grip (μ)', unit: '', min: 0.6, max: 1.6, step: 0.01 },
  { key: 'motor_peak_power_kw', label: 'Peak motor power', unit: 'kW', min: 4, max: 35, step: 0.5 },
  { key: 'motor_peak_torque_nm', label: 'Peak motor torque', unit: 'Nm', min: 20, max: 180, step: 1 },
  { key: 'gear_ratio', label: 'Final drive ratio', unit: ':1', min: 2, max: 9, step: 0.1 },
  { key: 'battery_nominal_voltage', label: 'Battery nominal voltage', unit: 'V', min: 48, max: 150, step: 1 },
  { key: 'battery_capacity_ah', label: 'Battery capacity', unit: 'Ah', min: 15, max: 120, step: 1 },
  { key: 'initial_soc_pct', label: 'Starting state of charge', unit: '%', min: 10, max: 100, step: 1 },
  { key: 'regen_efficiency_pct', label: 'Regen efficiency', unit: '%', min: 20, max: 95, step: 1 },
  { key: 'solar_irradiance_wm2', label: 'Solar irradiance', unit: 'W/m²', min: 0, max: 1200, step: 10 },
  { key: 'solar_array_area_m2', label: 'Solar array area', unit: 'm²', min: 1, max: 7, step: 0.1 }
];

const fmt = (n, digits = 1) => Number.isFinite(Number(n)) ? Number(n).toFixed(digits) : '—';
const clamp = (n, a, b) => Math.max(a, Math.min(b, n));

function pathFrom(data, width, height, pad = 8) {
  if (!data?.length) return '';
  const vals = data.map(Number).filter(Number.isFinite);
  if (!vals.length) return '';
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const span = hi - lo || 1;
  const stride = Math.max(1, Math.floor(vals.length / 500));
  return vals.filter((_, i) => i % stride === 0 || i === vals.length - 1)
    .map((v, i, arr) => {
      const originalIndex = Math.min(i * stride, vals.length - 1);
      const x = pad + originalIndex / Math.max(1, vals.length - 1) * (width - 2 * pad);
      const y = height - pad - (v - lo) / span * (height - 2 * pad);
      return `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
}

function MiniChart({ title, data, color = '#70e1d0', unit = '', cursor = 0, fill = false, label }) {
  const W = 640, H = 170, pad = 12;
  const values = data || [];
  const finite = values.filter(Number.isFinite);
  const min = finite.length ? Math.min(...finite) : 0;
  const max = finite.length ? Math.max(...finite) : 1;
  const span = max - min || 1;
  const path = pathFrom(values, W, H, pad);
  const cx = pad + cursor * (W - 2 * pad);
  const y = (v) => H - pad - (v - min) / span * (H - 2 * pad);
  const selected = finite[Math.min(finite.length - 1, Math.round(cursor * Math.max(0, finite.length - 1)))] ?? 0;
  return <section className="chart-card">
    <div className="chart-head">
      <div><div className="eyebrow">{title}</div><div className="chart-value">{fmt(selected, 2)} <small>{unit}</small></div></div>
      {label && <span className="chart-tag">{label}</span>}
    </div>
    <svg className="chart-svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title}>
      {[0, .25, .5, .75, 1].map(v => <line key={v} x1={pad} x2={W-pad} y1={pad+v*(H-2*pad)} y2={pad+v*(H-2*pad)} stroke="#26323e" strokeDasharray="3 7" />)}
      {fill && path && <path d={`${path} L${W-pad},${H-pad} L${pad},${H-pad} Z`} fill={color} opacity=".09" />}
      {path && <path d={path} fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />}
      <line x1={cx} x2={cx} y1={pad} y2={H-pad} stroke="#f5bc66" strokeDasharray="4 5" strokeWidth="1.5" />
      <circle cx={cx} cy={y(selected)} r="4.5" fill="#f5bc66" stroke="#111923" strokeWidth="2" />
    </svg>
    <div className="chart-foot"><span>START / S-F</span><span>END OF LAP</span></div>
  </section>;
}

function TrackView({ track, telemetry, index, colorMetric, onMetric }) {
  const [hover, setHover] = useState(null);
  const coords = track.length ? track : [];
  const bounds = useMemo(() => {
    if (!coords.length) return { minX: 0, maxX: 1, minY: 0, maxY: 1 };
    const xs = coords.map(p => p.x_m), ys = coords.map(p => p.y_m);
    return { minX: Math.min(...xs), maxX: Math.max(...xs), minY: Math.min(...ys), maxY: Math.max(...ys) };
  }, [coords]);
  const project = (p) => {
    const w = 760, h = 420, inset = 42;
    const sx = (w - 2 * inset) / Math.max(1, bounds.maxX - bounds.minX);
    const sy = (h - 2 * inset) / Math.max(1, bounds.maxY - bounds.minY);
    const scale = Math.min(sx, sy);
    const usedW = (bounds.maxX - bounds.minX) * scale;
    const usedH = (bounds.maxY - bounds.minY) * scale;
    return {
      x: (w - usedW) / 2 + (p.x_m - bounds.minX) * scale,
      y: h - ((h - usedH) / 2 + (p.y_m - bounds.minY) * scale)
    };
  };
  const points = coords.map(project);
  const line = points.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const carPoint = telemetry ? project({ x_m: telemetry.x_m[index], y_m: telemetry.y_m[index] }) : points[0];
  const selectedSpeed = telemetry?.speed_kmh?.[index] ?? 0;
  const metrics = telemetry ? telemetry[colorMetric] : [];
  const metricMin = metrics?.length ? Math.min(...metrics) : 0;
  const metricMax = metrics?.length ? Math.max(...metrics) : 1;
  const colorFor = (v) => {
    const t = clamp((v - metricMin) / (metricMax - metricMin || 1), 0, 1);
    return colorMetric === 'speed_kmh' ? `hsl(${195 - t*145} 78% ${46 + t*8}%)` : `hsl(${155 - t*115} 72% 55%)`;
  };
  const markers = [0.12, 0.32, 0.52, 0.72, 0.9].map((v, j) => {
    const p = points[Math.round(v * (points.length - 1))];
    return p ? { ...p, n: j + 1 } : null;
  }).filter(Boolean);
  return <section className="panel track-panel">
    <div className="panel-heading">
      <div><div className="eyebrow">CIRCUIT MAP / TELEMETRY TRACE</div><h2>Kari Motor Speedway</h2></div>
      <div className="track-tools">
        <select value={colorMetric} onChange={e => onMetric(e.target.value)} aria-label="Track color metric">
          <option value="speed_kmh">Speed</option><option value="motor_elec_power_kw">Motor power</option><option value="accel_y_g">Lateral G</option><option value="battery_soc_pct">Battery SOC</option>
        </select>
        <span className="live-pill"><i /> SIM VIEW</span>
      </div>
    </div>
    <div className="track-stage">
      <div className="track-grid" />
      <svg viewBox="0 0 760 420" className="track-svg" role="img" aria-label="Top-down view of Kari Motor Speedway simulated circuit">
        <defs><filter id="carGlow"><feGaussianBlur stdDeviation="5" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
        {line && <><polyline points={line} fill="none" stroke="#080c11" strokeWidth="42" strokeLinejoin="round" strokeLinecap="round" />
          <polyline points={line} fill="none" stroke="#526170" strokeWidth="31" strokeLinejoin="round" strokeLinecap="round" opacity=".62" />
          <polyline points={line} fill="none" stroke="#131f29" strokeWidth="26" strokeLinejoin="round" strokeLinecap="round" />
          <polyline points={line} fill="none" stroke="#7f909c" strokeWidth="1.2" strokeDasharray="10 12" opacity=".55" />
          {points.filter((p,i)=>i%5===0).map((p,i)=><circle key={i} cx={p.x} cy={p.y} r="1.5" fill="#9aabb5" opacity=".5" />)}
          {markers.map((p)=><g key={p.n}><circle cx={p.x} cy={p.y} r="12" fill="#111b23" stroke="#9aabb5" strokeOpacity=".35"/><text x={p.x} y={p.y+4} textAnchor="middle" fontSize="10" fill="#d9e5e9">{p.n}</text></g>)}
          {points.length > 0 && <g><circle cx={points[0].x} cy={points[0].y} r="8" fill="#f5bc66" stroke="#fff" strokeWidth="2"/><text x={points[0].x+14} y={points[0].y-13} fontSize="10" fill="#f5bc66" letterSpacing="1">START / FINISH</text></g>}
          {telemetry && metrics.map((v,i)=>{if(i%3!==0)return null; const p=points[i];return p?<circle key={i} cx={p.x} cy={p.y} r="2.7" fill={colorFor(v)} />:null;})}
          {carPoint && <g filter="url(#carGlow)" transform={`translate(${carPoint.x} ${carPoint.y})`}><circle r="14" fill="#70e1d0" opacity=".18"/><circle r="7" fill="#70e1d0" stroke="#effffb" strokeWidth="2"/><path d="M-2 1 L9 0 L-2 -3 Z" fill="#0b2021"/></g>}
        </>}
      </svg>
      <div className="map-legend"><span><i className="legend-cyan" /> HELIOS position</span><span><i className="legend-gold" /> Start / finish</span></div>
      {hover && <div className="map-hover">{hover}</div>}
    </div>
    <div className="track-bottom">
      <div><span className="eyebrow">TRACK DISTANCE</span><strong>{fmt(telemetry?.distance_m?.[index] ?? 0, 0)} <small>/ 2,120 m</small></strong></div>
      <div className="sector-track"><span className={telemetry?.sector?.[index]===1?'active':''}>S1</span><span className={telemetry?.sector?.[index]===2?'active':''}>S2</span><span className={telemetry?.sector?.[index]===3?'active':''}>S3</span></div>
      <div><span className="eyebrow">CURRENT SPEED</span><strong>{fmt(selectedSpeed,1)} <small>km/h</small></strong></div>
    </div>
  </section>;
}

function Stat({ label, value, unit, icon: Icon, tone = 'mint', detail }) {
  return <div className="stat-card">
    <div className={`stat-icon ${tone}`}><Icon size={16} /></div>
    <div className="stat-meta"><span>{label}</span><strong>{value} <small>{unit}</small></strong>{detail && <em>{detail}</em>}</div>
  </div>;
}

export default function App() {
  const [params, setParams] = useState(DEFAULTS);
  const [track, setTrack] = useState([]);
  const [telemetry, setTelemetry] = useState(null);
  const [summary, setSummary] = useState(null);
  const [simTime, setSimTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speedFactor, setSpeedFactor] = useState(1);
  const [colorMetric, setColorMetric] = useState('speed_kmh');
  const [activeTab, setActiveTab] = useState('power');
  const [showSetup, setShowSetup] = useState(false);
  const [preset, setPreset] = useState('baseline');
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [apiMode, setApiMode] = useState('browser');
  const raf = useRef(null);
  const previousFrame = useRef(0);
  const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

  const loadSimulation = useCallback(async (nextParams, nextTrack) => {
    setBusy(true);
    setError('');
    try {
      let result = null;
      if (apiBase) {
        try {
          const res = await fetch(`${apiBase}/api/simulate`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(nextParams)
          });
          if (!res.ok) throw new Error(`Backend returned ${res.status}`);
          result = await res.json();
          setApiMode('backend');
        } catch (e) {
          setApiMode('browser');
          setError(`Backend unavailable; using the in-browser physics engine. (${e.message})`);
        }
      }
      if (!result) {
        result = simulateLap(nextParams, nextTrack);
        setApiMode('browser');
      }
      setTelemetry(result.telemetry);
      setSummary(result.summary);
      setSimTime(0);
      setPlaying(false);
    } catch (e) {
      setError(e.message || 'Simulation could not be completed.');
    } finally {
      setBusy(false);
    }
  }, [apiBase]);

  useEffect(() => {
    let cancelled = false;
    fetch('/track_data.csv').then(r => {
      if (!r.ok) throw new Error('Could not load track geometry');
      return r.text();
    }).then(csv => {
      if (cancelled) return;
      const parsed = parseTrackCsv(csv);
      if (parsed.length < 20) throw new Error('Track geometry did not contain enough points');
      setTrack(parsed);
      loadSimulation(DEFAULTS, parsed);
    }).catch(e => {
      if (!cancelled) { setError(e.message); setBusy(false); }
    });
    return () => { cancelled = true; };
  }, [loadSimulation]);

  const maxTime = telemetry?.time_s?.[telemetry.time_s.length - 1] || 0;
  useEffect(() => {
    if (!playing || !telemetry) return;
    const tick = (stamp) => {
      if (!previousFrame.current) previousFrame.current = stamp;
      const delta = Math.min(0.08, (stamp - previousFrame.current) / 1000);
      previousFrame.current = stamp;
      setSimTime(prev => {
        const next = prev + delta * speedFactor;
        if (next >= maxTime) { setPlaying(false); return maxTime; }
        return next;
      });
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => { cancelAnimationFrame(raf.current); previousFrame.current = 0; };
  }, [playing, telemetry, speedFactor, maxTime]);

  const index = useMemo(() => {
    if (!telemetry?.time_s?.length) return 0;
    let lo = 0, hi = telemetry.time_s.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (telemetry.time_s[mid] < simTime) lo = mid + 1; else hi = mid;
    }
    return lo;
  }, [telemetry, simTime]);
  const current = useMemo(() => {
    if (!telemetry) return {};
    return Object.fromEntries(Object.entries(telemetry).map(([key, arr]) => [key, arr[index]]));
  }, [telemetry, index]);
  const cursor = maxTime > 0 ? simTime / maxTime : 0;

  const runWith = (next) => {
    setParams(next);
    loadSimulation(next, track);
  };
  const handlePreset = (key) => {
    setPreset(key);
    runWith({ ...DEFAULTS, ...PRESETS[key].patch });
  };
  const updateParam = (key, value) => setParams(p => ({ ...p, [key]: value }));
  const downloadCsv = () => {
    if (!telemetry) return;
    const keys = Object.keys(telemetry);
    const rows = [keys.join(',')];
    for (let i = 0; i < telemetry.time_s.length; i++) rows.push(keys.map(k => telemetry[k][i]).join(','));
    const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'helios-kari-lap-telemetry.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  const activeChartData = activeTab === 'power'
    ? [{ key: 'battery_soc_pct', title: 'BATTERY STATE OF CHARGE', unit: '%', color: '#70e1d0' }, { key: 'battery_current_a', title: 'PACK CURRENT', unit: 'A', color: '#f5bc66' }]
    : activeTab === 'dynamics'
    ? [{ key: 'accel_x_g', title: 'LONGITUDINAL ACCELERATION', unit: 'g', color: '#f5bc66' }, { key: 'accel_y_g', title: 'LATERAL ACCELERATION', unit: 'g', color: '#70a9f8' }]
    : [{ key: 'energy_consumed_kwh', title: 'GROSS ENERGY CONSUMED', unit: 'kWh', color: '#f5bc66' }, { key: 'energy_regenerated_kwh', title: 'REGEN ENERGY RECOVERED', unit: 'kWh', color: '#70e1d0' }];
  const maxOf = (key) => telemetry?.[key]?.length ? Math.max(...telemetry[key]) : 0;

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><div className="brand-mark"><Zap size={20} fill="currentColor" /></div><div><div className="brand-name">HELIOS <span>ENGINEERING</span></div><div className="brand-sub">SOLAR EV · DIGITAL TWIN · KARI MOTOR SPEEDWAY</div></div></div>
      <div className="topbar-right"><div className={`connection ${apiMode}`}><i />{apiMode === 'backend' ? 'CONNECTED TO API' : 'LOCAL PHYSICS ENGINE'}</div><button className="ghost-btn" onClick={() => setShowSetup(true)}><SlidersHorizontal size={15}/> VEHICLE SETUP</button><button className="primary-btn" onClick={() => runWith(params)} disabled={busy}><RotateCcw size={15}/> {busy ? 'SOLVING…' : 'RUN SIMULATION'}</button></div>
    </header>

    <main className="dashboard">
      <section className="welcome-row">
        <div><div className="overline"><span className="overline-line"/> SIMULATION CONTROL ROOM / 01</div><h1>Lap performance <i>analysis.</i></h1><p>Physics-led vehicle dynamics, energy flow and circuit telemetry — one lap at a time.</p></div>
        <div className="session-chip"><span className="session-dot"/><div><b>{busy ? 'SOLVING VEHICLE MODEL' : 'SIMULATION READY'}</b><small>{track.length.toLocaleString()} track samples · 2 m resolution</small></div></div>
      </section>

      {error && <div className="notice"><CircleHelp size={16}/><span>{error}</span><button onClick={() => setError('')}>Dismiss</button></div>}

      <section className="stat-grid">
        <Stat label="LAP TIME" value={summary ? fmt(summary.lap_time_s,2) : '—'} unit="SEC" icon={Timer} tone="mint" detail={summary ? 'Simulated flying lap' : 'Awaiting solver'} />
        <Stat label="TOP SPEED" value={summary ? fmt(summary.max_speed_kmh,1) : '—'} unit="KM/H" icon={Gauge} tone="blue" detail={`Current ${fmt(current.speed_kmh,1)} km/h`} />
        <Stat label="NET ENERGY" value={summary ? fmt(summary.net_energy_kwh,3) : '—'} unit="KWH" icon={Bolt} tone="amber" detail={summary ? `${fmt(summary.efficiency_wh_km,1)} Wh/km` : 'Battery + solar + regen'} />
        <Stat label="FINAL SOC" value={summary ? fmt(summary.final_soc_pct,1) : '—'} unit="%" icon={BatteryCharging} tone="violet" detail={summary ? `${fmt(summary.soc_delta_pct,2)}% over lap` : 'Pack state of charge'} />
      </section>

      <section className="main-grid">
        <TrackView track={track} telemetry={telemetry} index={index} colorMetric={colorMetric} onMetric={setColorMetric}/>
        <aside className="right-column">
          <section className="panel telemetry-panel">
            <div className="panel-heading"><div><div className="eyebrow">LIVE VEHICLE TELEMETRY</div><h2>Car state <span className="tiny-pulse"/></h2></div><span className="small-code">T+{fmt(simTime,2)}s</span></div>
            <div className="speed-readout"><div className="speed-number">{fmt(current.speed_kmh,1)}<small>km/h</small></div><div className="speed-arc"><span>VELOCITY</span><b>{fmt((current.speed_kmh || 0)/Math.max(summary?.max_speed_kmh || 1,1)*100,0)}%</b></div></div>
            <div className="telemetry-list">
              <div><span><Activity size={14}/> Motor speed</span><b>{fmt(current.motor_rpm,0)} <small>rpm</small></b></div>
              <div><span><Bolt size={14}/> Motor electrical</span><b>{fmt(current.motor_elec_power_kw,2)} <small>kW</small></b></div>
              <div><span><BatteryCharging size={14}/> Pack voltage</span><b>{fmt(current.battery_voltage_v,1)} <small>V</small></b></div>
              <div><span><Waves size={14}/> Pack current</span><b>{fmt(current.battery_current_a,1)} <small>A</small></b></div>
              <div><span><CarFront size={14}/> Lateral G</span><b>{fmt(current.accel_y_g,2)} <small>g</small></b></div>
              <div><span><Sun size={14}/> Solar input</span><b>{fmt(current.solar_power_w,0)} <small>W</small></b></div>
            </div>
            <div className="energy-bars">
              <div className="energy-bar-head"><span>BATTERY SOC</span><b>{fmt(current.battery_soc_pct,1)}%</b></div>
              <div className="bar-track"><i style={{ width: `${clamp(current.battery_soc_pct || 0,0,100)}%` }}/></div>
              <div className="energy-bar-head"><span>MOTOR LOAD</span><b>{fmt((current.motor_elec_power_kw || 0)/Math.max(params.motor_peak_power_kw,1)*100,0)}%</b></div>
              <div className="bar-track gold"><i style={{ width: `${clamp((current.motor_elec_power_kw || 0)/Math.max(params.motor_peak_power_kw,1)*100,0,100)}%` }}/></div>
            </div>
          </section>
          <section className="panel lap-control">
            <div className="panel-heading"><div><div className="eyebrow">LAP PLAYBACK</div><h2>Replay controls</h2></div><span className="small-code">{fmt(maxTime,2)} SEC</span></div>
            <div className="playback-buttons"><button className="play-main" onClick={() => { if (simTime >= maxTime) setSimTime(0); setPlaying(v => !v); }} disabled={!telemetry || busy}>{playing ? <Pause size={17} fill="currentColor"/> : <Play size={17} fill="currentColor"/>}{playing ? 'PAUSE' : 'PLAY LAP'}</button><button className="icon-button" onClick={() => {setPlaying(false);setSimTime(0);}} title="Restart lap"><RotateCcw size={17}/></button></div>
            <input className="time-slider" type="range" min="0" max={Math.max(maxTime,0.1)} step="0.02" value={Math.min(simTime,maxTime || 0)} onChange={e => {setPlaying(false);setSimTime(Number(e.target.value));}}/>
            <div className="time-labels"><span>00:00.00</span><b>{fmt(simTime,2)}s</b><span>{fmt(maxTime,2)}s</span></div>
            <div className="speed-controls"><span>PLAYBACK RATE</span>{[0.5,1,2,4].map(s=><button key={s} className={speedFactor===s?'selected':''} onClick={()=>setSpeedFactor(s)}>{s}×</button>)}</div>
          </section>
        </aside>
      </section>

      <section className="analysis-section">
        <div className="analysis-title"><div><div className="eyebrow">ENGINEERING TELEMETRY / 02</div><h2>Data acquisition</h2></div><div className="chart-caption">Cursor follows lap playback · Hover-free live values</div></div>
        <div className="chart-grid">
          <MiniChart title="VELOCITY PROFILE" data={telemetry?.speed_kmh} color="#70e1d0" unit="km/h" cursor={cursor} fill/>
          <MiniChart title="MOTOR ELECTRICAL POWER" data={telemetry?.motor_elec_power_kw} color="#f5bc66" unit="kW" cursor={cursor} fill/>
        </div>
        <div className="data-tabs">{[{id:'power',label:'BATTERY & POWERTRAIN'},{id:'dynamics',label:'VEHICLE DYNAMICS'},{id:'energy',label:'ENERGY BALANCE'}].map(t=><button key={t.id} onClick={()=>setActiveTab(t.id)} className={activeTab===t.id?'active':''}>{t.label}</button>)}<button className="export-inline" onClick={downloadCsv} disabled={!telemetry}><Download size={14}/> EXPORT CSV</button></div>
        <div className="chart-grid lower">
          {activeChartData.map(c=><MiniChart key={c.key} title={c.title} data={telemetry?.[c.key]} unit={c.unit} color={c.color} cursor={cursor}/>)}
        </div>
      </section>

      <section className="bottom-grid">
        <section className="panel summary-panel"><div className="panel-heading"><div><div className="eyebrow">SECTOR TIMING</div><h2>Lap split analysis</h2></div><span className="small-code">3 SECTORS</span></div>
          {[{name:'SECTOR 01',time:summary?.sector_1_s},{name:'SECTOR 02',time:summary?.sector_2_s},{name:'SECTOR 03',time:summary?.sector_3_s}].map((s,i)=><div className="sector-row" key={s.name}><span className="sector-index">0{i+1}</span><span>{s.name}</span><div className="sector-trackbar"><i style={{width:`${(s.time || 0)/Math.max(summary?.lap_time_s || 1,1)*100}%`}}/></div><b>{fmt(s.time,2)}<small> s</small></b></div>)}
        </section>
        <section className="panel summary-panel"><div className="panel-heading"><div><div className="eyebrow">ENERGY ACCOUNTING</div><h2>Lap energy balance</h2></div><Sun size={18} color="#f5bc66"/></div>
          <div className="balance-row"><span>Gross battery discharge</span><b>{fmt(summary?.energy_consumed_kwh,3)} kWh</b></div>
          <div className="balance-row"><span>Regenerative recovery</span><b className="positive">−{fmt(summary?.energy_regenerated_kwh,3)} kWh</b></div>
          <div className="balance-row"><span>Solar energy harvested</span><b className="positive">−{fmt(summary?.solar_energy_harvested_kwh,3)} kWh</b></div>
          <div className="balance-total"><span>NET BATTERY ENERGY</span><strong>{fmt(summary?.net_energy_kwh,3)} <small>kWh</small></strong></div>
        </section>
        <section className="panel summary-panel"><div className="panel-heading"><div><div className="eyebrow">MODEL CONFIGURATION</div><h2>Vehicle parameters</h2></div><button className="text-link" onClick={()=>setShowSetup(true)}>EDIT <Settings2 size={13}/></button></div>
          <div className="config-summary"><div><span>Mass</span><b>{fmt(params.vehicle_mass,0)} kg</b></div><div><span>Peak power</span><b>{fmt(params.motor_peak_power_kw,1)} kW</b></div><div><span>Grip coefficient</span><b>μ {fmt(params.friction_coefficient,2)}</b></div><div><span>Solar input</span><b>{fmt(params.solar_irradiance_wm2,0)} W/m²</b></div></div>
        </section>
      </section>

      <footer className="footer"><div>HELIOS <span>ENGINEERING SIMULATION</span></div><p>Track geometry is an analytical reconstruction. Vehicle parameters are configurable engineering assumptions, not measured vehicle data.</p><span>MODEL BUILD 1.1 · {apiMode==='backend'?'API':'BROWSER SOLVER'}</span></footer>
    </main>

    {showSetup && <div className="drawer-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)setShowSetup(false);}}>
      <aside className="setup-drawer">
        <div className="drawer-head"><div><div className="eyebrow">SIMULATION INPUTS</div><h2>Vehicle setup</h2><p>Adjust physical parameters and solve a new lap.</p></div><button className="icon-button" onClick={()=>setShowSetup(false)}>×</button></div>
        <div className="preset-block"><label>QUICK SETUP</label><div className="preset-grid">{Object.entries(PRESETS).map(([key,p])=><button key={key} className={preset===key?'selected':''} onClick={()=>{setPreset(key);setParams({...DEFAULTS,...p.patch});}}>{p.label}</button>)}</div></div>
        <div className="parameter-list">{PARAMS.map(p=><div className="parameter" key={p.key}><div className="parameter-label"><label htmlFor={p.key}>{p.label}</label><b>{params[p.key]} <small>{p.unit}</small></b></div><input id={p.key} type="range" min={p.min} max={p.max} step={p.step} value={params[p.key]} onChange={e=>{updateParam(p.key,Number(e.target.value));setPreset('custom');}}/></div>)}</div>
        <div className="drawer-actions"><button className="ghost-btn" onClick={()=>{setParams(DEFAULTS);setPreset('baseline');}}>RESET DEFAULTS</button><button className="primary-btn" disabled={busy} onClick={()=>{setShowSetup(false);loadSimulation(params,track);}}><Play size={15}/> {busy?'SOLVING…':'APPLY & RUN'}</button></div>
      </aside>
    </div>}
  </div>;
}
