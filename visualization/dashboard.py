"""
Telemetry Dashboard UI Components & Styling
Streamlit automotive digital twin interface design with dark aesthetic and telemetry metrics.
"""

from typing import Dict, Any
import streamlit as st
import pandas as pd


CUSTOM_CSS = """
<style>
/* Main Dark Cockpit Theme */
.stApp {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
}

/* Metric Cards */
.metric-container {
    background: linear-gradient(135deg, #161b22 0%, #1f242c 100%);
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}

.metric-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8b949e;
    margin-bottom: 4px;
}

.metric-value {
    font-size: 1.5rem;
    font-weight: 700;
    font-family: "JetBrains Mono", Consolas, monospace;
    color: #58a6ff;
}

.metric-value-cyan { color: #00e5ff !important; }
.metric-value-gold { color: #ffd600 !important; }
.metric-value-green { color: #00e676 !important; }
.metric-value-red { color: #ff1744 !important; }
.metric-value-orange { color: #ff9100 !important; }

.metric-unit {
    font-size: 0.8rem;
    font-weight: 400;
    color: #8b949e;
    margin-left: 4px;
}

/* Header Banner */
.cockpit-header {
    background: linear-gradient(90deg, #161b22 0%, #0d1117 100%);
    border-left: 4px solid #00e5ff;
    padding: 14px 20px;
    border-radius: 4px;
    margin-bottom: 20px;
}

.cockpit-title {
    font-size: 1.6rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    color: #f0f6fc;
    margin: 0;
}

.cockpit-subtitle {
    font-size: 0.85rem;
    color: #8b949e;
    margin-top: 4px;
}

/* Sector Badge */
.sector-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
}
.sector-1 { background-color: rgba(0, 229, 255, 0.15); color: #00e5ff; border: 1px solid #00e5ff; }
.sector-2 { background-color: rgba(255, 214, 0, 0.15); color: #ffd600; border: 1px solid #ffd600; }
.sector-3 { background-color: rgba(0, 230, 118, 0.15); color: #00e676; border: 1px solid #00e676; }

/* Disclaimer Banner */
.disclaimer-box {
    background-color: rgba(56, 139, 253, 0.1);
    border: 1px solid rgba(56, 139, 253, 0.4);
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 0.8rem;
    color: #8b949e;
    margin-bottom: 15px;
}
</style>
"""


def render_cockpit_header():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown("""
    <div class="cockpit-header">
        <div class="cockpit-title">⚡ HELIOS DIGITAL TWIN // KARI MOTOR SPEEDWAY</div>
        <div class="cockpit-subtitle">PHYSICS-BASED SOLAR EV LAP SIMULATION & REAL-TIME TELEMETRY SYSTEM</div>
    </div>
    <div class="disclaimer-box">
        <b>Engineering Notice:</b> Circuit geometry is modeled via a validated parametric spline representing Kari Motor Speedway (2,120 m, 14 turns, anti-clockwise). Vehicle parameters represent provisional solar racing prototypes and can be tuned live in the sidebar.
    </div>
    """, unsafe_allow_html=True)


def render_metric_card(col, label: str, value: str, unit: str = "", color_class: str = "metric-value-cyan"):
    html = f"""
    <div class="metric-container">
        <div class="metric-label">{label}</div>
        <div class="metric-value {color_class}">{value}<span class="metric-unit">{unit}</span></div>
    </div>
    """
    col.markdown(html, unsafe_allow_html=True)


def render_telemetry_hud(snap: Dict[str, Any]):
    """Renders the top live digital telemetry HUD bar."""
    if not snap:
        return

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    # 1. Speed
    render_metric_card(c1, "Vehicle Speed", f"{snap.get('speed_kmh', 0.0):.1f}", "km/h", "metric-value-cyan")

    # 2. Motor RPM
    render_metric_card(c2, "Motor RPM", f"{snap.get('motor_rpm', 0.0):.0f}", "RPM", "metric-value-orange")

    # 3. Motor Power
    render_metric_card(c3, "Motor Power", f"{snap.get('motor_elec_power_kw', 0.0):.2f}", "kW", "metric-value-green")

    # 4. Battery SOC
    render_metric_card(c4, "Battery SOC", f"{snap.get('battery_soc_pct', 0.0):.1f}", "%", "metric-value-cyan")

    # 5. Battery Power
    batt_kw = snap.get('battery_power_kw', 0.0)
    p_color = "metric-value-red" if batt_kw > 0 else "metric-value-green"
    p_label = "Batt Discharge" if batt_kw >= 0 else "Batt Regen/Solar"
    render_metric_card(c5, p_label, f"{abs(batt_kw):.2f}", "kW", p_color)

    # 6. Lateral G
    lat_g = snap.get('accel_y_g', 0.0)
    render_metric_card(c6, "Lateral Accel", f"{lat_g:+.2f}", "g", "metric-value-gold")


def render_secondary_hud(snap: Dict[str, Any]):
    """Renders secondary telemetry metrics: forces, voltages, currents."""
    if not snap:
        return

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    # 1. Long Accel
    long_g = snap.get('accel_x_g', 0.0)
    render_metric_card(c1, "Long. Accel", f"{long_g:+.2f}", "g", "metric-value-cyan")

    # 2. Battery Voltage
    v = snap.get('battery_voltage_v', 0.0)
    render_metric_card(c2, "Pack Voltage", f"{v:.1f}", "V", "metric-value-gold")

    # 3. Pack Current
    curr = snap.get('battery_current_a', 0.0)
    render_metric_card(c3, "Pack Current", f"{curr:+.1f}", "A", "metric-value-orange")

    # 4. Solar Harvest Power
    solar_w = snap.get('solar_power_w', 0.0)
    render_metric_card(c4, "Solar Array Power", f"{solar_w:.0f}", "W", "metric-value-green")

    # 5. Regen Braking Power
    regen_kw = snap.get('regen_power_kw', 0.0)
    render_metric_card(c5, "Regen Power", f"{regen_kw:.2f}", "kW", "metric-value-green")

    # 6. Net Energy Consumed
    net_kwh = snap.get('net_energy_kwh', 0.0)
    render_metric_card(c6, "Net Energy Draw", f"{net_kwh:.3f}", "kWh", "metric-value-cyan")

