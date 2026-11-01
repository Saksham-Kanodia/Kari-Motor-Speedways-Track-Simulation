import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity, BatteryCharging, Bolt, CarFront, ChevronDown, CircleHelp,
  Download, Gauge, Pause, Play, RotateCcw, Settings2, Sun, Timer,
  Waves, Zap, SlidersHorizontal, Cpu, Radio, ChartNoAxesCombined,
  LayoutDashboard, Route, BatteryFull, BookOpen, ChevronRight, ArrowUpRight, Crosshair
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
  const [hoverAt, setHoverAt] = useState(null);
  const W = 640, H = 170, pad = 12;
  const values = data || [];
  const finite = values.filter(Number.isFinite);
  const min = finite.length ? Math.min(...finite) : 0;
  const max = finite.length ? Math.max(...finite) : 1;
  const span = max - min || 1;
  const path = pathFrom(values, W, H, pad);
  const cx = pad + cursor * (W - 2 * pad);
  const y = (v) => H - pad - (v - min) / span * (H - 2 * pad);
  const selectedIndex = hoverAt === null ? Math.round(cursor * Math.max(0, finite.length - 1)) : hoverAt;
  const selected = finite[Math.min(finite.length - 1, selectedIndex)] ?? 0;
  const activeCursor = pad + selectedIndex / Math.max(1, finite.length - 1) * (W - 2 * pad);
  return <section className="chart-card">
    <div className="chart-head">
      <div><div className="eyebrow">{title}</div><div className="chart-value">{fmt(selected, 2)} <small>{unit}</small></div></div>
      {label && <span className="chart-tag">{label}</span>}
    </div>
    <svg className="chart-svg interactive-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title} onPointerMove={e => { const rect=e.currentTarget.getBoundingClientRect(); const t=clamp((e.clientX-rect.left)/rect.width,0,1); setHoverAt(Math.round(t*Math.max(0,finite.length-1))); }} onPointerLeave={()=>setHoverAt(null)}>
      {[0, .25, .5, .75, 1].map(v => <line key={v} x1={pad} x2={W-pad} y1={pad+v*(H-2*pad)} y2={pad+v*(H-2*pad)} stroke="#26323e" strokeDasharray="3 7" />)}
      {fill && path && <path d={`${path} L${W-pad},${H-pad} L${pad},${H-pad} Z`} fill={color} opacity=".09" />}
      {path && <path d={path} fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />}
      <line x1={activeCursor} x2={activeCursor} y1={pad} y2={H-pad} stroke="#f5bc66" strokeDasharray="4 5" strokeWidth="1.5" />
      <circle cx={activeCursor} cy={y(selected)} r="5.5" fill="#f5bc66" stroke="#111923" strokeWidth="2" />
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
        {line && <><polyline points={line} fill="none" stroke="#080c11" strokeWidth="30" strokeLinejoin="round" strokeLinecap="round" />
          <polyline points={line} fill="none" stroke="#526170" strokeWidth="22" strokeLinejoin="round" strokeLinecap="round" opacity=".62" />
          <polyline points={line} fill="none" stroke="#131f29" strokeWidth="16" strokeLinejoin="round" strokeLinecap="round" />
          <polyline points={line} fill="none" stroke="#7f909c" strokeWidth="1.2" strokeDasharray="10 12" opacity=".55" />
          {points.filter((p,i)=>i%5===0).map((p,i)=><circle key={i} cx={p.x} cy={p.y} r="1.5" fill="#9aabb5" opacity=".5" />)}
          {markers.map((p)=><g key={p.n}><circle cx={p.x} cy={p.y} r="12" fill="#111b23" stroke="#9aabb5" strokeOpacity=".35"/><text x={p.x} y={p.y+4} textAnchor="middle" fontSize="10" fill="#d9e5e9">{p.n}</text></g>)}
          {points.length > 0 && <g><circle cx={points[0].x} cy={points[0].y} r="8" fill="#f5bc66" stroke="#fff" strokeWidth="2"/><text x={points[0].x+14} y={points[0].y-13} fontSize="10" fill="#f5bc66" letterSpacing="1">START / FINISH</text></g>}
          {telemetry && metrics.map((v,i)=>{if(i%3!==0)return null; const p=points[i];return p?<circle key={i} cx={p.x} cy={p.y} r="2.7" fill={colorFor(v)} />:null;})}
          {carPoint && <g filter="url(#carGlow)" transform={`translate(${carPoint.x} ${carPoint.y})`}><circle r="14" fill="#70e1d0" opacity=".18"/><circle r="7" fill="#70e1d0" stroke="#effffb" strokeWidth="2"/><path d="M-2 1 L9 0 L-2 -3 Z" fill="#0b2021"/></g>}
          <g transform="translate(710 52)" opacity=".72"><path d="M0 14 L0 -12 M-6 -4 L0 -12 L6 -4" fill="none" stroke="#d7e1e8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/><text x="0" y="28" textAnchor="middle" fill="#d7e1e8" fontSize="10" letterSpacing="1.5">N</text></g>
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
  const [page, setPage] = useState('overview');
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

  const pages = [
    {id:'overview',label:'Overview',icon:LayoutDashboard},
    {id:'simulation',label:'Live simulation',icon:Route},
    {id:'energy',label:'Vehicle & energy',icon:BatteryFull},
    {id:'analysis',label:'Track analysis',icon:ChartNoAxesCombined},
    {id:'model',label:'Engineering notes',icon:BookOpen}
  ];
  const copy = {
    overview:['MISSION CONTROL / 01','Lap overview.','Key results and quick access to the simulator.'],
    simulation:['LIVE SIMULATION / 02','Follow the car around the circuit.','Replay the lap and inspect vehicle telemetry as the car moves.'],
    energy:['VEHICLE SYSTEMS / 03','Understand the energy budget.','Battery behaviour, motor demand, solar generation and regenerative recovery.'],
    analysis:['CIRCUIT INTELLIGENCE / 04','Read the track, not just the lap time.','Sector performance, speed envelope and vehicle dynamics across the circuit.'],
    model:['ENGINEERING NOTES / 05','Know what the model assumes.','A transparent summary of equations and limitations behind each result.']
  };
  const goto = id => {setPage(id);window.scrollTo({top:0,behavior:'smooth'});};
  const sectors = [{name:'SECTOR 01',time:summary?.sector_1_s},{name:'SECTOR 02',time:summary?.sector_2_s},{name:'SECTOR 03',time:summary?.sector_3_s}];
  const chartGrid = items => <div className="chart-grid">{items.map(c=><MiniChart key={c.key} title={c.title} data={telemetry?.[c.key]} unit={c.unit} color={c.color} cursor={cursor} fill/>)}</div>;
  const overviewCharts = [{key:'speed_kmh',title:'VELOCITY PROFILE',unit:'km/h',color:'#70e1d0'},{key:'motor_elec_power_kw',title:'MOTOR POWER',unit:'kW',color:'#f5bc66'}];
  const energyCharts = [
    {key:'battery_soc_pct',title:'BATTERY STATE OF CHARGE',unit:'%',color:'#70e1d0'},
    {key:'battery_current_a',title:'PACK CURRENT',unit:'A',color:'#f5bc66'},
    {key:'battery_voltage_v',title:'PACK VOLTAGE',unit:'V',color:'#70a9f8'},
    {key:'battery_power_kw',title:'BATTERY POWER',unit:'kW',color:'#be9bff'},
    {key:'solar_power_w',title:'SOLAR GENERATION',unit:'W',color:'#f5bc66'},
    {key:'regen_power_kw',title:'REGENERATIVE POWER',unit:'kW',color:'#70e1d0'}
  ];
  const dynamicsCharts = [
    {key:'accel_x_g',title:'LONGITUDINAL ACCELERATION',unit:'g',color:'#f5bc66'},
    {key:'accel_y_g',title:'LATERAL ACCELERATION',unit:'g',color:'#70a9f8'},
    {key:'motor_rpm',title:'MOTOR SPEED',unit:'rpm',color:'#70e1d0'},
    {key:'motor_elec_power_kw',title:'MOTOR ELECTRICAL POWER',unit:'kW',color:'#be9bff'}
  ];
  const TrackCard = () => <TrackView track={track} telemetry={telemetry} index={index} colorMetric={colorMetric} onMetric={setColorMetric}/>;
  const TelemetryCard = () => <section className="panel telemetry-panel">
    <div className="panel-heading"><div><div className="eyebrow">LIVE VEHICLE TELEMETRY</div><h2>Car state <span className="tiny-pulse"/></h2></div><span className="small-code">T+{fmt(simTime,2)}s</span></div>
    <div className="speed-readout"><div className="speed-number">{fmt(current.speed_kmh,1)}<small>km/h</small></div><div className="speed-arc"><span>VELOCITY</span><b>{fmt((current.speed_kmh||0)/Math.max(summary?.max_speed_kmh||1,1)*100,0)}%</b></div></div>
    <div className="telemetry-list">
      <div><span><Activity size={14}/> Motor speed</span><b>{fmt(current.motor_rpm,0)} <small>rpm</small></b></div>
      <div><span><Bolt size={14}/> Motor electrical</span><b>{fmt(current.motor_elec_power_kw,2)} <small>kW</small></b></div>
      <div><span><BatteryCharging size={14}/> Pack voltage</span><b>{fmt(current.battery_voltage_v,1)} <small>V</small></b></div>
      <div><span><Waves size={14}/> Pack current</span><b>{fmt(current.battery_current_a,1)} <small>A</small></b></div>
      <div><span><CarFront size={14}/> Lateral G</span><b>{fmt(current.accel_y_g,2)} <small>g</small></b></div>
      <div><span><Sun size={14}/> Solar input</span><b>{fmt(current.solar_power_w,0)} <small>W</small></b></div>
    </div>
    <div className="energy-bars"><div className="energy-bar-head"><span>BATTERY SOC</span><b>{fmt(current.battery_soc_pct,1)}%</b></div><div className="bar-track"><i style={{width:`${clamp(current.battery_soc_pct||0,0,100)}%`}}/></div><div className="energy-bar-head"><span>MOTOR LOAD</span><b>{fmt((current.motor_elec_power_kw||0)/Math.max(params.motor_peak_power_kw,1)*100,0)}%</b></div><div className="bar-track gold"><i style={{width:`${clamp((current.motor_elec_power_kw||0)/Math.max(params.motor_peak_power_kw,1)*100,0,100)}%`}}/></div></div>
  </section>;
  const PlaybackCard = () => <section className="panel lap-control">
    <div className="panel-heading"><div><div className="eyebrow">LAP PLAYBACK</div><h2>Replay controls</h2></div><span className="small-code">{fmt(maxTime,2)} SEC</span></div>
    <div className="playback-buttons"><button className="play-main" onClick={()=>{if(simTime>=maxTime)setSimTime(0);setPlaying(v=>!v);}} disabled={!telemetry||busy}>{playing?<Pause size={17} fill="currentColor"/>:<Play size={17} fill="currentColor"/>}{playing?'PAUSE':'PLAY LAP'}</button><button className="icon-button" onClick={()=>{setPlaying(false);setSimTime(0);}} title="Restart lap"><RotateCcw size={17}/></button></div>
    <input className="time-slider" type="range" min="0" max={Math.max(maxTime,0.1)} step="0.02" value={Math.min(simTime,maxTime||0)} onChange={e=>{setPlaying(false);setSimTime(Number(e.target.value));}}/>
    <div className="time-labels"><span>00:00.00</span><b>{fmt(simTime,2)}s</b><span>{fmt(maxTime,2)}s</span></div>
    <div className="speed-controls"><span>PLAYBACK RATE</span>{[0.5,1,2,4].map(s=><button key={s} className={speedFactor===s?'selected':''} onClick={()=>setSpeedFactor(s)}>{s}×</button>)}</div>
  </section>;
  return <div className="app-shell">
    <header className="topbar">
      <button className="brand brand-button" onClick={()=>goto('overview')} aria-label="Go to overview"><div className="brand-mark"><Zap size={20} fill="currentColor"/></div><div><div className="brand-name">HELIOS <span>ENGINEERING</span></div><div className="brand-sub">SOLAR EV · DIGITAL TWIN · KARI MOTOR SPEEDWAY</div></div></button>
      <div className="topbar-right"><div className={`connection ${apiMode}`}><i/>{apiMode==='backend'?'CONNECTED TO API':'LOCAL PHYSICS ENGINE'}</div><button className="ghost-btn" onClick={()=>setShowSetup(true)}><SlidersHorizontal size={15}/> VEHICLE SETUP</button><button className="primary-btn" onClick={()=>runWith(params)} disabled={busy}><RotateCcw size={15}/>{busy?'SOLVING…':'RUN SIMULATION'}</button></div>
    </header>
    <nav className="section-nav" aria-label="Main sections">{pages.map(({id,label,icon:Icon},i)=><button key={id} className={page===id?'active':''} onClick={()=>goto(id)}><Icon size={15}/><span>{label}</span><small>0{i+1}</small></button>)}</nav>
    <main className="dashboard">
      <section className="welcome-row"><div><div className="overline"><span className="overline-line"/>{copy[page][0]}</div><h1>{copy[page][1]}</h1><p>{copy[page][2]}</p></div><div className="session-chip"><span className="session-dot"/><div><b>{busy?'SOLVING VEHICLE MODEL':'SIMULATION READY'}</b><small>{track.length.toLocaleString()} track samples · 2 m resolution</small></div></div></section>
      {error&&<div className="notice"><CircleHelp size={16}/><span>{error}</span><button onClick={()=>setError('')}>Dismiss</button></div>}
      {page==='overview'&&<>
        <section className="stat-grid"><Stat label="LAP TIME" value={summary?fmt(summary.lap_time_s,2):'—'} unit="SEC" icon={Timer} tone="mint" detail="Simulated flying lap"/><Stat label="TOP SPEED" value={summary?fmt(summary.max_speed_kmh,1):'—'} unit="KM/H" icon={Gauge} tone="blue" detail={`Current ${fmt(current.speed_kmh,1)} km/h`}/><Stat label="NET ENERGY" value={summary?fmt(summary.net_energy_kwh,3):'—'} unit="KWH" icon={Bolt} tone="amber" detail={summary?`${fmt(summary.efficiency_wh_km,1)} Wh/km`:'Battery + solar + regen'}/><Stat label="FINAL SOC" value={summary?fmt(summary.final_soc_pct,1):'—'} unit="%" icon={BatteryCharging} tone="violet" detail={summary?`${fmt(summary.soc_delta_pct,2)}% over lap`:'Pack state of charge'}/></section>
        <div className="overview-grid"><div className="overview-feature"><div className="eyebrow">THE CIRCUIT / 2.12 KM</div><h2>Explore the lap.</h2><p>Follow the vehicle around the reconstructed Kari Motor Speedway layout. Replay the solver output and inspect telemetry at any point.</p><button className="primary-btn" onClick={()=>goto('simulation')}>OPEN LIVE SIMULATION <ArrowUpRight size={15}/></button></div><div className="overview-route"><TrackCard/></div></div>
        <div className="section-teaser-row">{[{id:'energy',icon:BatteryFull,title:'Vehicle & energy',desc:'Battery, motor, solar and regeneration.'},{id:'analysis',icon:ChartNoAxesCombined,title:'Track analysis',desc:'Sector splits, grip and velocity profile.'},{id:'model',icon:BookOpen,title:'Engineering notes',desc:'Equations, assumptions and limitations.'}].map(({id,icon:Icon,title,desc},i)=><button className="teaser-card" key={id} onClick={()=>goto(id)}><div className="teaser-icon"><Icon size={18}/></div><span className="eyebrow">SECTION 0{i+3}</span><h3>{title}</h3><p>{desc}</p><b>EXPLORE SECTION <ChevronRight size={14}/></b></button>)}</div>
        chartGrid(overviewCharts)
      </>}
      {page==='simulation'&&<><div className="stat-grid compact-stats"><Stat label="CURRENT SPEED" value={fmt(current.speed_kmh,1)} unit="KM/H" icon={Gauge}/><Stat label="DISTANCE" value={fmt(current.distance_m,0)} unit="M" icon={Route}/><Stat label="SECTOR" value={current.sector||'—'} unit="" icon={Crosshair}/><Stat label="ELAPSED" value={fmt(simTime,2)} unit="SEC" icon={Timer}/></div><div className="simulation-layout"><TrackCard/><aside className="right-column"><TelemetryCard/><PlaybackCard/></aside></div>chartGrid(overviewCharts)</>}
      {page==='energy'&&<><section className="stat-grid"><Stat label="GROSS DISCHARGE" value={fmt(summary?.energy_consumed_kwh,3)} unit="KWH" icon={Bolt} tone="amber"/><Stat label="REGEN RECOVERY" value={fmt(summary?.energy_regenerated_kwh,3)} unit="KWH" icon={Waves} tone="mint"/><Stat label="SOLAR HARVEST" value={fmt(summary?.solar_energy_harvested_kwh,3)} unit="KWH" icon={Sun} tone="amber"/><Stat label="ENERGY INTENSITY" value={fmt(summary?.efficiency_wh_km,1)} unit="WH/KM" icon={Activity} tone="blue"/></section><section className="panel energy-overview"><div className="panel-heading"><div><div className="eyebrow">LAP ENERGY ACCOUNTING</div><h2>Where the energy goes</h2></div><span className="small-code">CUMULATIVE / KWH</span></div><div className="energy-flow-grid"><div><span>Battery discharged</span><b>{fmt(summary?.energy_consumed_kwh,3)} <small>kWh</small></b></div><div><span>Regenerative braking</span><b>{fmt(summary?.energy_regenerated_kwh,3)} <small>kWh</small></b></div><div><span>Solar harvested</span><b>{fmt(summary?.solar_energy_harvested_kwh,3)} <small>kWh</small></b></div><div className="net-flow"><span>Net battery draw</span><b>{fmt(summary?.net_energy_kwh,3)} <small>kWh</small></b></div></div></section><div className="analysis-title"><div><div className="eyebrow">POWERTRAIN CHANNELS</div><h2>Electrical telemetry</h2></div><span className="chart-caption">Hover over any plot to inspect its value</span></div>{'chartGrid(energyCharts)'}</>}
      {page==='analysis'&&<><div className="stat-grid"><Stat label="AVERAGE SPEED" value={fmt(summary?.avg_speed_kmh,1)} unit="KM/H" icon={Gauge}/><Stat label="PEAK LATERAL G" value={fmt(summary?.max_lat_accel_g,2)} unit="G" icon={Activity} tone="blue"/><Stat label="MAX ACCELERATION" value={fmt(summary?.max_long_accel_mps2,2)} unit="M/S²" icon={Bolt} tone="amber"/><Stat label="MINIMUM SPEED" value={fmt(summary?.min_speed_kmh,1)} unit="KM/H" icon={Timer} tone="violet"/></div><TrackCard/><section className="panel sector-analysis"><div className="panel-heading"><div><div className="eyebrow">TIMING / THREE SECTORS</div><h2>Sector comparison</h2></div><span className="small-code">TOTAL {fmt(summary?.lap_time_s,2)} S</span></div>{sectors.map((s,i)=><div className="sector-row large" key={s.name}><span className="sector-index">0{i+1}</span><span>{s.name}</span><div className="sector-trackbar"><i style={{width:`${(s.time||0)/Math.max(summary?.lap_time_s||1,1)*100}%`}}/></div><b>{fmt(s.time,2)}<small> s</small></b></div>)}</section><div className="analysis-title"><div><div className="eyebrow">DYNAMICS / GRIP RESPONSE</div><h2>Vehicle response</h2></div><span className="chart-caption">Longitudinal and lateral channels over lap time</span></div>{'chartGrid(dynamicsCharts)'}</>}
      {page==='model'&&<><section className="model-intro panel"><div className="eyebrow">HELIOS / MODEL DESCRIPTION</div><h2>Physics first. Assumptions visible.</h2><p>The simulator uses a discretised track centreline and a two-pass velocity solver. Each output is an engineering estimate based on the current parameter set, not a measured lap from a real vehicle.</p></section><div className="model-grid">{[['01','Track geometry','Image-aligned centreline traced from the supplied Kari layout map, rescaled to approximately 2.12 km and sampled at 2 m spacing. Corner radii and sector boundaries are inferred from a low-resolution schematic, not surveyed CAD.'],['02','Longitudinal dynamics','Newton’s second law with aerodynamic drag, rolling resistance, motor traction and service braking. The speed envelope uses forward acceleration and backward braking passes.'],['03','Tyre grip','Curvature-dependent cornering speed and a friction-circle approximation reserve grip for lateral acceleration while accelerating or braking.'],['04','Electric powertrain','Motor torque is held up to base speed, then follows a constant-power limit until rotational cut-off.'],['05','Battery model','A resistance-based equivalent circuit estimates terminal voltage, current, SOC integration and energy throughput.'],['06','Solar and regeneration','Solar generation uses irradiance, panel area and assumed efficiencies. Braking energy recovery is bounded by regen and battery charge limits.']].map(([n,t,d])=><article className="model-card" key={n}><span>{n}</span><h3>{t}</h3><p>{d}</p></article>)}</div><section className="panel assumptions-panel"><div className="eyebrow">CURRENT BASELINE INPUTS</div><div className="assumption-grid">{PARAMS.map(p=><div key={p.key}><span>{p.label}</span><b>{fmt(params[p.key],p.step<1?3:1)} {p.unit}</b></div>)}</div></section><div className="notice"><CircleHelp size={16}/><span>Results are not validated lap-time predictions. Track shape, tyre behaviour, thermal effects, drivetrain maps, elevation and weather are simplified or assumed.</span></div></>}
      <footer className="footer"><div>HELIOS <span>ENGINEERING SIMULATION</span></div><p>Analytical circuit geometry · configurable engineering assumptions · browser-side solver</p><span>MODEL BUILD 1.2 · {apiMode==='backend'?'API':'BROWSER SOLVER'}</span></footer>
    </main>
    {showSetup&&<div className="drawer-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)setShowSetup(false);}}><aside className="setup-drawer"><div className="drawer-head"><div><div className="eyebrow">SIMULATION INPUTS</div><h2>Vehicle setup</h2><p>Adjust physical parameters and solve a new lap.</p></div><button className="icon-button" onClick={()=>setShowSetup(false)}>×</button></div><div className="preset-block"><label>QUICK SETUP</label><div className="preset-grid">{Object.entries(PRESETS).map(([key,p])=><button key={key} className={preset===key?'selected':''} onClick={()=>{setPreset(key);setParams({...DEFAULTS,...p.patch});}}>{p.label}</button>)}</div></div><div className="parameter-list">{PARAMS.map(p=><div className="parameter" key={p.key}><div className="parameter-label"><label htmlFor={p.key}>{p.label}</label><b>{params[p.key]} <small>{p.unit}</small></b></div><input id={p.key} type="range" min={p.min} max={p.max} step={p.step} value={params[p.key]} onChange={e=>{updateParam(p.key,Number(e.target.value));setPreset('custom');}}/></div>)}</div><div className="drawer-actions"><button className="ghost-btn" onClick={()=>{setParams(DEFAULTS);setPreset('baseline');}}>RESET DEFAULTS</button><button className="primary-btn" disabled={busy} onClick={()=>{setShowSetup(false);loadSimulation(params,track);}}><Play size={15}/>{busy?'SOLVING…':'APPLY & RUN'}</button></div></aside></div>}
  </div>;
}
