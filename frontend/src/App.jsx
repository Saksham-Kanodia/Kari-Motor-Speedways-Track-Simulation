import React, { useState, useEffect, useRef } from 'react'
import {
  Zap, Play, Pause, RotateCcw, FastForward, Sliders, Download,
  Activity, Gauge, Battery, Sun, Flag, ChevronRight, RefreshCw, Layers
} from 'lucide-react'

// Dark Plotly template layout helper
const PLOT_THEME = {
  paper_bgcolor: '#121720',
  plot_bgcolor: '#0a0d12',
  font: { family: 'Inter, sans-serif', color: '#f0f6fc', size: 10 },
  margin: { l: 45, r: 25, t: 35, b: 35 },
  xaxis: { gridcolor: '#222b3a', zerolinecolor: '#222b3a', color: '#8b949e' },
  yaxis: { gridcolor: '#222b3a', zerolinecolor: '#222b3a', color: '#8b949e' }
}

export default function App() {
  const [telemetry, setTelemetry] = useState(null)
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [simTime, setSimTime] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [playbackSpeed, setPlaybackSpeed] = useState(2.0)
  const [colorMetric, setColorMetric] = useState('speed_kmh')
  const [activeTab, setActiveTab] = useState('pwr')
  const [showConfig, setShowConfig] = useState(false)
  const [apiConnected, setApiConnected] = useState(false)
  const [recomputing, setRecomputing] = useState(false)

  // Config parameters
  const [params, setParams] = useState({
    vehicle_mass: 320.0,
    drag_coefficient: 0.20,
    frontal_area: 1.15,
    rolling_resistance_coeff: 0.007,
    friction_coefficient: 1.15,
    motor_peak_power_kw: 12.0,
    motor_peak_torque_nm: 75.0,
    gear_ratio: 4.2,
    battery_nominal_voltage: 96.0,
    battery_capacity_ah: 50.0,
    initial_soc_pct: 90.0,
    regen_efficiency_pct: 70.0,
    solar_irradiance_wm2: 850.0,
    solar_array_area_m2: 4.0
  })

  const trackDivRef = useRef(null)
  const speedDivRef = useRef(null)
  const powerDivRef = useRef(null)
  const tabPlot1Ref = useRef(null)
  const tabPlot2Ref = useRef(null)

  // Fetch initial baseline lap telemetry
  useEffect(() => {
    async function loadInitialData() {
      try {
        const res = await fetch('/api/default-lap')
        if (res.ok) {
          const data = await res.json()
          setTelemetry(data.telemetry)
          setSummary(data.summary)
          setApiConnected(true)
        } else {
          throw new Error('API returned non-200')
        }
      } catch (err) {
        console.warn('FastAPI backend not reachable, using fallback baseline:', err)
        setApiConnected(false)
      } finally {
        setLoading(false)
      }
    }
    loadInitialData()
  }, [])

  // Animation playback loop
  useEffect(() => {
    let animId
    let lastStamp = performance.now()

    function step(now) {
      if (isPlaying && telemetry) {
        const delta = (now - lastStamp) / 1000.0
        const maxTime = telemetry.time_s[telemetry.time_s.length - 1]
        setSimTime(prev => {
          const next = prev + delta * playbackSpeed
          if (next >= maxTime) {
            setIsPlaying(false)
            return maxTime
          }
          return next
        })
      }
      lastStamp = now
      if (isPlaying) {
        animId = requestAnimationFrame(step)
      }
    }

    if (isPlaying) {
      animId = requestAnimationFrame(step)
    }
    return () => cancelAnimationFrame(animId)
  }, [isPlaying, telemetry, playbackSpeed])

  // Current interpolated index & snapshot
  const currentIndex = telemetry ? Math.min(
    telemetry.time_s.findIndex(t => t >= simTime) === -1 ? telemetry.time_s.length - 1 : telemetry.time_s.findIndex(t => t >= simTime),
    telemetry.time_s.length - 1
  ) : 0

  const snap = telemetry ? {
    speed_kmh: telemetry.speed_kmh[currentIndex],
    motor_rpm: telemetry.motor_rpm[currentIndex],
    motor_elec_power_kw: telemetry.motor_elec_power_kw[currentIndex],
    battery_soc_pct: telemetry.battery_soc_pct[currentIndex],
    battery_current_a: telemetry.battery_current_a[currentIndex],
    battery_voltage_v: telemetry.battery_voltage_v[currentIndex],
    battery_power_kw: telemetry.battery_power_kw[currentIndex],
    accel_x_g: telemetry.accel_x_g[currentIndex],
    accel_y_g: telemetry.accel_y_g[currentIndex],
    solar_power_w: telemetry.solar_power_w[currentIndex],
    regen_power_kw: telemetry.regen_power_kw[currentIndex],
    net_energy_kwh: telemetry.net_energy_kwh[currentIndex],
    distance_m: telemetry.distance_m[currentIndex],
    x_m: telemetry.x_m[currentIndex],
    y_m: telemetry.y_m[currentIndex],
    sector: telemetry.sector[currentIndex]
  } : {}

  const maxLapTime = telemetry ? telemetry.time_s[telemetry.time_s.length - 1] : 74.0

  // Re-run simulation via FastAPI
  async function handleRecompute() {
    setRecomputing(true)
    try {
      const res = await fetch('/api/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      })
      if (res.ok) {
        const data = await res.json()
        setTelemetry(data.telemetry)
        setSummary(data.summary)
        setSimTime(0)
        setIsPlaying(false)
        setApiConnected(true)
      }
    } catch (e) {
      alert('Error connecting to simulation API: ' + e.message)
    } finally {
      setRecomputing(false)
    }
  }

  // Render or update Plotly Track Map
  useEffect(() => {
    if (!window.Plotly || !telemetry || !trackDivRef.current) return

    const colorArr = telemetry[colorMetric] || telemetry.speed_kmh
    const traceOutline = {
      x: telemetry.x_m,
      y: telemetry.y_m,
      mode: 'lines',
      line: { color: '#1c2432', width: 10 },
      hoverinfo: 'skip',
      showlegend: false
    }

    const traceCenterline = {
      x: telemetry.x_m,
      y: telemetry.y_m,
      mode: 'markers',
      marker: {
        size: 5,
        color: colorArr,
        colorscale: colorMetric === 'sector' ? 'Viridis' : 'Plasma',
        colorbar: {
          title: { text: colorMetric, font: { color: '#f0f6fc', size: 9 } },
          tickfont: { color: '#8b949e', size: 8 },
          len: 0.7,
          thickness: 10,
          x: 1.02
        }
      },
      name: 'Centerline'
    }

    const traceStartFinish = {
      x: [telemetry.x_m[0]],
      y: [telemetry.y_m[0]],
      mode: 'markers+text',
      marker: { size: 10, color: '#ffd600', symbol: 'diamond' },
      text: ['S/F'],
      textposition: 'bottom center',
      textfont: { color: '#ffd600', size: 9 },
      name: 'Start/Finish'
    }

    const traceCar = {
      x: [snap.x_m],
      y: [snap.y_m],
      mode: 'markers',
      marker: {
        size: 16,
        color: '#00e5ff',
        line: { color: '#ffffff', width: 2 },
        symbol: 'circle'
      },
      name: 'HELIOS'
    }

    const layout = {
      ...PLOT_THEME,
      title: { text: '<b>KARI MOTOR SPEEDWAY // TOP-DOWN TRACK</b>', font: { size: 12, color: '#f0f6fc' } },
      height: 420,
      showlegend: false,
      yaxis: { scaleanchor: 'x', scaleratio: 1, ...PLOT_THEME.yaxis }
    }

    window.Plotly.react(trackDivRef.current, [traceOutline, traceCenterline, traceStartFinish, traceCar], layout, { responsive: true, displayModeBar: false })
  }, [telemetry, colorMetric, snap.x_m, snap.y_m])

  // Render Speed & Power traces
  useEffect(() => {
    if (!window.Plotly || !telemetry) return

    if (speedDivRef.current) {
      const traceSpeed = {
        x: telemetry.time_s,
        y: telemetry.speed_kmh,
        mode: 'lines',
        line: { color: '#00e5ff', width: 2.2 },
        name: 'Speed (km/h)'
      }
      const layout = {
        ...PLOT_THEME,
        title: { text: '<b>VELOCITY PROFILE (km/h)</b>', font: { size: 11, color: '#f0f6fc' } },
        height: 200,
        shapes: [{
          type: 'line',
          x0: simTime, x1: simTime,
          y0: 0, y1: Math.max(...telemetry.speed_kmh) * 1.1,
          line: { color: '#ffd600', width: 1.5, dash: 'dash' }
        }]
      }
      window.Plotly.react(speedDivRef.current, [traceSpeed], layout, { responsive: true, displayModeBar: false })
    }

    if (powerDivRef.current) {
      const tracePower = {
        x: telemetry.time_s,
        y: telemetry.motor_elec_power_kw,
        mode: 'lines',
        line: { color: '#00e676', width: 2 },
        name: 'Motor Power (kW)'
      }
      const layout = {
        ...PLOT_THEME,
        title: { text: '<b>MOTOR ELECTRICAL POWER (kW)</b>', font: { size: 11, color: '#f0f6fc' } },
        height: 200,
        shapes: [{
          type: 'line',
          x0: simTime, x1: simTime,
          y0: 0, y1: Math.max(...telemetry.motor_elec_power_kw) * 1.1,
          line: { color: '#ffd600', width: 1.5, dash: 'dash' }
        }]
      }
      window.Plotly.react(powerDivRef.current, [tracePower], layout, { responsive: true, displayModeBar: false })
    }
  }, [telemetry, simTime])

  // Render Tabbed Plots
  useEffect(() => {
    if (!window.Plotly || !telemetry) return

    if (activeTab === 'pwr') {
      if (tabPlot1Ref.current) {
        const traceSOC = {
          x: telemetry.time_s,
          y: telemetry.battery_soc_pct,
          mode: 'lines',
          line: { color: '#00e5ff', width: 2.2 },
          name: 'SOC (%)'
        }
        window.Plotly.react(tabPlot1Ref.current, [traceSOC], { ...PLOT_THEME, title: { text: '<b>BATTERY STATE OF CHARGE (%)</b>', font: { size: 11, color: '#f0f6fc' } }, height: 260 }, { responsive: true, displayModeBar: false })
      }
      if (tabPlot2Ref.current) {
        const traceCurrent = {
          x: telemetry.time_s,
          y: telemetry.battery_current_a,
          mode: 'lines',
          line: { color: '#ff9100', width: 2 },
          name: 'Current (A)'
        }
        window.Plotly.react(tabPlot2Ref.current, [traceCurrent], { ...PLOT_THEME, title: { text: '<b>PACK CURRENT (A) [+Disch, -Regen]</b>', font: { size: 11, color: '#f0f6fc' } }, height: 260 }, { responsive: true, displayModeBar: false })
      }
    } else if (activeTab === 'dyn') {
      if (tabPlot1Ref.current) {
        const traceLat = { x: telemetry.time_s, y: telemetry.accel_y_g, mode: 'lines', line: { color: '#ff1744', width: 1.8 }, name: 'Lat Accel (g)' }
        const traceLong = { x: telemetry.time_s, y: telemetry.accel_x_g, mode: 'lines', line: { color: '#00e5ff', width: 1.8 }, name: 'Long Accel (g)' }
        window.Plotly.react(tabPlot1Ref.current, [traceLat, traceLong], { ...PLOT_THEME, title: { text: '<b>CHASSIS G-FORCES</b>', font: { size: 11, color: '#f0f6fc' } }, height: 260 }, { responsive: true, displayModeBar: false })
      }
      if (tabPlot2Ref.current) {
        const traceGG = {
          x: telemetry.accel_y_g,
          y: telemetry.accel_x_g,
          mode: 'markers',
          marker: { size: 4, color: telemetry.speed_kmh, colorscale: 'Plasma', opacity: 0.7 },
          name: 'G-G Scatter'
        }
        const currGG = {
          x: [snap.accel_y_g],
          y: [snap.accel_x_g],
          mode: 'markers',
          marker: { size: 12, color: '#00e5ff', symbol: 'circle' },
          name: 'Current'
        }
        window.Plotly.react(tabPlot2Ref.current, [traceGG, currGG], { ...PLOT_THEME, title: { text: '<b>FRICTION CIRCLE (G-G DIAGRAM)</b>', font: { size: 11, color: '#f0f6fc' } }, height: 260, yaxis: { scaleanchor: 'x', scaleratio: 1, ...PLOT_THEME.yaxis } }, { responsive: true, displayModeBar: false })
      }
    } else if (activeTab === 'nrg') {
      if (tabPlot1Ref.current) {
        const traceGross = { x: telemetry.distance_m, y: telemetry.energy_consumed_kwh, mode: 'lines', line: { color: '#ff9100', width: 2 }, name: 'Gross Discharged (kWh)' }
        const traceRegen = { x: telemetry.distance_m, y: telemetry.energy_regenerated_kwh, mode: 'lines', line: { color: '#00e676', width: 2 }, name: 'Regen Harvest (kWh)' }
        const traceSolar = { x: telemetry.distance_m, y: telemetry.solar_energy_kwh, mode: 'lines', line: { color: '#ffd600', width: 2 }, name: 'Solar Harvest (kWh)' }
        window.Plotly.react(tabPlot1Ref.current, [traceGross, traceRegen, traceSolar], { ...PLOT_THEME, title: { text: '<b>CUMULATIVE ENERGY BALANCES (kWh)</b>', font: { size: 11, color: '#f0f6fc' } }, height: 260 }, { responsive: true, displayModeBar: false })
      }
      if (tabPlot2Ref.current) {
        const traceNet = { x: telemetry.distance_m, y: telemetry.net_energy_kwh, mode: 'lines', line: { color: '#00e5ff', width: 2.2 }, name: 'Net Energy Draw (kWh)' }
        window.Plotly.react(tabPlot2Ref.current, [traceNet], { ...PLOT_THEME, title: { text: '<b>NET BATTERY ENERGY CONSUMPTION (kWh)</b>', font: { size: 11, color: '#f0f6fc' } }, height: 260 }, { responsive: true, displayModeBar: false })
      }
    }
  }, [activeTab, telemetry, snap.accel_x_g, snap.accel_y_g])

  // Download full telemetry CSV
  function downloadCSV() {
    if (!telemetry) return
    const keys = Object.keys(telemetry)
    const rowCount = telemetry[keys[0]].length
    let csv = keys.join(',') + '\n'
    for (let i = 0; i < rowCount; i++) {
      csv += keys.map(k => telemetry[k][i]).join(',') + '\n'
    }
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'helios_kari_speedway_telemetry.csv'
    a.click()
  }

  return (
    <div className="min-h-screen bg-[#0a0d12] text-[#f0f6fc] flex flex-col">
      {/* Top Motorsport Header */}
      <header className="border-b border-[#222b3a] bg-[#121720] px-6 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded bg-[#00e5ff]/10 border border-[#00e5ff]/30 text-[#00e5ff]">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-lg font-extrabold tracking-wider text-white flex items-center gap-2">
              HELIOS <span className="text-xs text-[#00e5ff] font-semibold px-2 py-0.5 rounded bg-[#00e5ff]/15 border border-[#00e5ff]/30">DIGITAL TWIN</span>
            </h1>
            <p className="text-xs text-[#8b949e]">Kari Motor Speedway Lap Simulator // Coimbatore, India</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <span className={`text-xs px-2.5 py-1 rounded-full flex items-center gap-1.5 font-medium border ${
            apiConnected ? 'bg-[#00e676]/10 text-[#00e676] border-[#00e676]/30' : 'bg-[#ffd600]/10 text-[#ffd600] border-[#ffd600]/30'
          }`}>
            <span className={`w-2 h-2 rounded-full ${apiConnected ? 'bg-[#00e676]' : 'bg-[#ffd600]'}`}></span>
            {apiConnected ? 'FastAPI Online' : 'Static Mode'}
          </span>

          <button
            onClick={() => setShowConfig(!showConfig)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded bg-[#1c2432] hover:bg-[#273244] border border-[#2e3b50] text-[#f0f6fc] transition"
          >
            <Sliders className="w-3.5 h-3.5 text-[#00e5ff]" />
            Parameters
          </button>

          <button
            onClick={downloadCSV}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded bg-[#1c2432] hover:bg-[#273244] border border-[#2e3b50] text-[#f0f6fc] transition"
          >
            <Download className="w-3.5 h-3.5 text-[#00e676]" />
            Export CSV
          </button>
        </div>
      </header>

      {/* Primary Live Telemetry HUD Bar */}
      <div className="px-6 py-3 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
        <div className="hud-card">
          <div className="text-[10px] font-semibold text-[#8b949e] uppercase tracking-wider">Speed</div>
          <div className="text-2xl font-bold mono text-[#00e5ff]">
            {(snap.speed_kmh || 0).toFixed(1)} <span className="text-xs font-normal text-[#8b949e]">km/h</span>
          </div>
        </div>

        <div className="hud-card">
          <div className="text-[10px] font-semibold text-[#8b949e] uppercase tracking-wider">Motor RPM</div>
          <div className="text-2xl font-bold mono text-[#ff9100]">
            {(snap.motor_rpm || 0).toFixed(0)} <span className="text-xs font-normal text-[#8b949e]">RPM</span>
          </div>
        </div>

        <div className="hud-card">
          <div className="text-[10px] font-semibold text-[#8b949e] uppercase tracking-wider">Motor Power</div>
          <div className="text-2xl font-bold mono text-[#00e676]">
            {(snap.motor_elec_power_kw || 0).toFixed(2)} <span className="text-xs font-normal text-[#8b949e]">kW</span>
          </div>
        </div>

        <div className="hud-card">
          <div className="text-[10px] font-semibold text-[#8b949e] uppercase tracking-wider">Battery SOC</div>
          <div className="text-2xl font-bold mono text-[#00e5ff]">
            {(snap.battery_soc_pct || 0).toFixed(1)} <span className="text-xs font-normal text-[#8b949e]">%</span>
          </div>
        </div>

        <div className="hud-card">
          <div className="text-[10px] font-semibold text-[#8b949e] uppercase tracking-wider">Pack Current</div>
          <div className="text-2xl font-bold mono text-[#d500f9]">
            {(snap.battery_current_a || 0).toFixed(1)} <span className="text-xs font-normal text-[#8b949e]">A</span>
          </div>
        </div>

        <div className="hud-card">
          <div className="text-[10px] font-semibold text-[#8b949e] uppercase tracking-wider">Lateral Accel</div>
          <div className="text-2xl font-bold mono text-[#ffd600]">
            {(snap.accel_y_g || 0).toFixed(2)} <span className="text-xs font-normal text-[#8b949e]">g</span>
          </div>
        </div>
      </div>

      {/* Main Visual Arena */}
      <div className="flex-1 px-6 pb-6 grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Track Map & Playback Controls */}
        <div className="lg:col-span-7 flex flex-col space-y-3">
          <div className="hud-card flex-1 flex flex-col p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-[#f0f6fc]">CIRCUIT TRACKING</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-[#1c2738] text-[#00e5ff] font-semibold">Sector {snap.sector || 1}</span>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="text-[#8b949e]">Color metric:</span>
                <select
                  value={colorMetric}
                  onChange={e => setColorMetric(e.target.value)}
                  className="bg-[#0a0d12] border border-[#273142] text-xs text-[#f0f6fc] rounded px-2 py-1 outline-none"
                >
                  <option value="speed_kmh">Speed (km/h)</option>
                  <option value="motor_elec_power_kw">Motor Power (kW)</option>
                  <option value="accel_y_g">Lateral Accel (g)</option>
                  <option value="sector">Circuit Sector (1-3)</option>
                </select>
              </div>
            </div>

            <div ref={trackDivRef} className="w-full flex-1 rounded bg-[#0a0d12] overflow-hidden" />

            {/* Playback Control Bar */}
            <div className="mt-3 pt-3 border-t border-[#222b3a] flex flex-col space-y-2">
              <div className="flex items-center justify-between text-xs text-[#8b949e]">
                <span>Lap Time: <b className="text-white mono">{simTime.toFixed(2)}s</b> / {maxLapTime.toFixed(2)}s</span>
                <span>Distance: <b className="text-white mono">{(snap.distance_m || 0).toFixed(0)}m</b> / 2120m</span>
              </div>

              <input
                type="range"
                min="0"
                max={maxLapTime}
                step="0.1"
                value={simTime}
                onChange={e => {
                  setSimTime(parseFloat(e.target.value))
                  setIsPlaying(false)
                }}
                className="slider-custom"
              />

              <div className="flex items-center justify-between pt-1">
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setIsPlaying(!isPlaying)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#00e5ff] text-[#0a0d12] font-bold text-xs hover:bg-[#33ebff] transition"
                  >
                    {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                    {isPlaying ? 'Pause' : 'Play'}
                  </button>

                  <button
                    onClick={() => { setSimTime(0); setIsPlaying(false); }}
                    className="p-1.5 rounded bg-[#1c2432] text-[#8b949e] hover:text-white border border-[#273142] transition"
                    title="Reset to Start"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="flex items-center space-x-1 text-xs">
                  <span className="text-[#8b949e] mr-1">Speed:</span>
                  {[0.5, 1, 2, 5].map(s => (
                    <button
                      key={s}
                      onClick={() => setPlaybackSpeed(s)}
                      className={`px-2 py-0.5 rounded text-[11px] font-semibold ${playbackSpeed === s ? 'bg-[#00e5ff] text-[#0a0d12]' : 'bg-[#1c2432] text-[#8b949e] hover:text-white'}`}
                    >
                      {s}x
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Key Traces & Multi-Channel Tabs */}
        <div className="lg:col-span-5 flex flex-col space-y-3">
          <div className="hud-card p-3">
            <div ref={speedDivRef} className="w-full h-[200px]" />
          </div>

          <div className="hud-card p-3">
            <div ref={powerDivRef} className="w-full h-[200px]" />
          </div>
        </div>
      </div>

      {/* Multi-Channel Telemetry Tabs */}
      <div className="px-6 pb-6">
        <div className="hud-card p-4">
          <div className="flex items-center border-b border-[#222b3a] pb-3 mb-4 space-x-2 overflow-x-auto">
            <button
              onClick={() => setActiveTab('pwr')}
              className={`tab-btn ${activeTab === 'pwr' ? 'active' : ''}`}
            >
              🔋 Battery & Powertrain
            </button>
            <button
              onClick={() => setActiveTab('dyn')}
              className={`tab-btn ${activeTab === 'dyn' ? 'active' : ''}`}
            >
              🏎️ Dynamics & Friction Circle
            </button>
            <button
              onClick={() => setActiveTab('nrg')}
              className={`tab-btn ${activeTab === 'nrg' ? 'active' : ''}`}
            >
              ☀️ Energy & Balances
            </button>
            <button
              onClick={() => setActiveTab('sum')}
              className={`tab-btn ${activeTab === 'sum' ? 'active' : ''}`}
            >
              🏁 Lap Performance Summary
            </button>
          </div>

          {activeTab !== 'sum' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div ref={tabPlot1Ref} className="w-full h-[260px] bg-[#0a0d12] rounded p-2" />
              <div ref={tabPlot2Ref} className="w-full h-[260px] bg-[#0a0d12] rounded p-2" />
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="card p-4 bg-[#0a0d12] rounded border border-[#273142]">
                <h4 className="font-bold text-[#00e5ff] mb-2 uppercase tracking-wider">Lap Timing</h4>
                <div className="space-y-1.5 text-[#8b949e]">
                  <p>Total Lap Time: <b className="text-white font-mono">{summary ? summary.lap_time_s.toFixed(2) : '73.93'}s</b></p>
                  <p>Sector 1: <b className="text-white font-mono">{summary ? summary.sector_1_s.toFixed(2) : '23.81'}s</b></p>
                  <p>Sector 2: <b className="text-white font-mono">{summary ? summary.sector_2_s.toFixed(2) : '28.95'}s</b></p>
                  <p>Sector 3: <b className="text-white font-mono">{summary ? summary.sector_3_s.toFixed(2) : '21.16'}s</b></p>
                  <p>Average Speed: <b className="text-white font-mono">{summary ? summary.avg_speed_kmh.toFixed(1) : '103.1'} km/h</b></p>
                </div>
              </div>

              <div className="card p-4 bg-[#0a0d12] rounded border border-[#273142]">
                <h4 className="font-bold text-[#00e676] mb-2 uppercase tracking-wider">Kinematic Limits</h4>
                <div className="space-y-1.5 text-[#8b949e]">
                  <p>Top Speed: <b className="text-white font-mono">{summary ? summary.max_speed_kmh.toFixed(1) : '129.2'} km/h</b></p>
                  <p>Min Apex Speed: <b className="text-white font-mono">{summary ? summary.min_speed_kmh.toFixed(1) : '51.4'} km/h</b></p>
                  <p>Max Long Accel: <b className="text-white font-mono">{summary ? summary.max_long_accel_mps2.toFixed(2) : '2.31'} m/s²</b></p>
                  <p>Max Braking Decel: <b className="text-white font-mono">{summary ? summary.max_braking_decel_mps2.toFixed(2) : '11.47'} m/s²</b></p>
                  <p>Peak Lateral G: <b className="text-white font-mono">{summary ? summary.max_lat_accel_g.toFixed(2) : '1.13'} g</b></p>
                </div>
              </div>

              <div className="card p-4 bg-[#0a0d12] rounded border border-[#273142]">
                <h4 className="font-bold text-[#ffd600] mb-2 uppercase tracking-wider">Energy & Efficiency</h4>
                <div className="space-y-1.5 text-[#8b949e]">
                  <p>Gross Energy Consumed: <b className="text-white font-mono">{summary ? summary.energy_consumed_kwh.toFixed(3) : '0.224'} kWh</b></p>
                  <p>Regenerated Harvest: <b className="text-white font-mono">{summary ? summary.energy_regenerated_kwh.toFixed(3) : '0.016'} kWh</b></p>
                  <p>Solar PV Gain: <b className="text-white font-mono">{summary ? summary.solar_energy_harvested_kwh.toFixed(3) : '0.015'} kWh</b></p>
                  <p>Net Energy Draw: <b className="text-white font-mono">{summary ? summary.net_energy_kwh.toFixed(3) : '0.208'} kWh</b></p>
                  <p>Efficiency: <b className="text-white font-mono">{summary ? summary.efficiency_wh_km.toFixed(1) : '98.3'} Wh/km</b></p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Slide-out Parameter Tuning Panel */}
      {showConfig && (
        <div className="fixed inset-y-0 right-0 w-80 bg-[#121720] border-l border-[#273142] p-5 shadow-2xl z-50 flex flex-col overflow-y-auto">
          <div className="flex items-center justify-between pb-3 border-b border-[#222b3a] mb-4">
            <h3 className="font-bold text-sm text-[#00e5ff] flex items-center gap-1.5">
              <Sliders className="w-4 h-4" />
              VEHICLE PARAMETERS
            </h3>
            <button onClick={() => setShowConfig(false)} className="text-[#8b949e] hover:text-white text-xs">✕ Close</button>
          </div>

          <div className="space-y-4 flex-1 text-xs">
            <div>
              <label className="text-[#8b949e] block mb-1">Total Mass (kg): <b className="text-white">{params.vehicle_mass}</b></label>
              <input type="range" min="200" max="450" step="5" value={params.vehicle_mass} onChange={e => setParams({...params, vehicle_mass: parseFloat(e.target.value)})} className="slider-custom" />
            </div>

            <div>
              <label className="text-[#8b949e] block mb-1">Drag Coeff (Cd): <b className="text-white">{params.drag_coefficient}</b></label>
              <input type="range" min="0.12" max="0.35" step="0.01" value={params.drag_coefficient} onChange={e => setParams({...params, drag_coefficient: parseFloat(e.target.value)})} className="slider-custom" />
            </div>

            <div>
              <label className="text-[#8b949e] block mb-1">Motor Peak Power (kW): <b className="text-white">{params.motor_peak_power_kw}</b></label>
              <input type="range" min="5" max="25" step="0.5" value={params.motor_peak_power_kw} onChange={e => setParams({...params, motor_peak_power_kw: parseFloat(e.target.value)})} className="slider-custom" />
            </div>

            <div>
              <label className="text-[#8b949e] block mb-1">Motor Peak Torque (Nm): <b className="text-white">{params.motor_peak_torque_nm}</b></label>
              <input type="range" min="30" max="130" step="5" value={params.motor_peak_torque_nm} onChange={e => setParams({...params, motor_peak_torque_nm: parseFloat(e.target.value)})} className="slider-custom" />
            </div>

            <div>
              <label className="text-[#8b949e] block mb-1">Tyre Grip (μ): <b className="text-white">{params.friction_coefficient}</b></label>
              <input type="range" min="0.8" max="1.4" step="0.05" value={params.friction_coefficient} onChange={e => setParams({...params, friction_coefficient: parseFloat(e.target.value)})} className="slider-custom" />
            </div>

            <div>
              <label className="text-[#8b949e] block mb-1">Solar Irradiance (W/m²): <b className="text-white">{params.solar_irradiance_wm2}</b></label>
              <input type="range" min="0" max="1100" step="50" value={params.solar_irradiance_wm2} onChange={e => setParams({...params, solar_irradiance_wm2: parseFloat(e.target.value)})} className="slider-custom" />
            </div>
          </div>

          <button
            onClick={handleRecompute}
            disabled={recomputing}
            className="w-full mt-4 py-2 px-3 rounded bg-[#00e5ff] text-[#0a0d12] font-bold text-xs hover:bg-[#33ebff] transition flex items-center justify-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${recomputing ? 'animate-spin' : ''}`} />
            {recomputing ? 'Simulating Lap...' : 'Recalculate Physics'}
          </button>
        </div>
      )}
    </div>
  )
}

