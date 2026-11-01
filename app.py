"""
HELIOS — Physics-Based Solar EV Digital Twin & Kari Motor Speedway Simulator
Main Streamlit Application Entrypoint
"""

import os
import time
import tempfile

# Set temporary directory for Matplotlib cache to avoid Windows permission warnings
os.environ["MPLCONFIGDIR"] = os.path.join(tempfile.gettempdir(), "matplotlib")

import streamlit as st
import numpy as np
import pandas as pd

from config import (
    HeliosConfig,
    EnvironmentalParameters,
    AerodynamicParameters,
    ChassisParameters,
    PowertrainParameters,
    BatteryParameters,
    SolarArrayParameters,
    TrackParameters
)
from simulation.track import KariTrack
from simulation.lap_simulator import LapSimulator
from simulation.telemetry import TelemetryManager
from visualization.dashboard import render_cockpit_header, render_telemetry_hud, render_secondary_hud
from visualization.plots import HeliosPlotter


# ---------------- PAGE CONFIGURATION ----------------
st.set_page_config(
    page_title="HELIOS — Solar EV Digital Twin // Kari Motor Speedway",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ---------------- INITIALIZATION & CACHING ----------------
@st.cache_resource
def get_default_track():
    return KariTrack(resolution_m=2.0)


@st.cache_data
def run_simulation(config_dict: dict):
    # Reconstruct HeliosConfig from cached dictionary
    cfg = HeliosConfig(
        env=EnvironmentalParameters(**config_dict["env"]),
        aero=AerodynamicParameters(**config_dict["aero"]),
        chassis=ChassisParameters(**config_dict["chassis"]),
        powertrain=PowertrainParameters(**config_dict["powertrain"]),
        battery=BatteryParameters(**config_dict["battery"]),
        solar=SolarArrayParameters(**config_dict["solar"]),
        track=TrackParameters(**config_dict["track"])
    )
    track = get_default_track()
    simulator = LapSimulator(config=cfg, track=track)
    telemetry_df, summary = simulator.run_lap()
    return telemetry_df, summary, cfg


# ---------------- SIDEBAR: VEHICLE & SIMULATION CONFIGURATION ----------------
st.sidebar.markdown("## ⚙️ VEHICLE CONFIGURATION")
st.sidebar.caption("Provisional engineering parameters. Adjust and click recompute.")

with st.sidebar.expander("🏎️ Chassis & Aerodynamics", expanded=False):
    veh_mass = st.slider("Total Mass (Curb + Driver) [kg]", 200.0, 500.0, 320.0, 5.0)
    drag_cd = st.slider("Drag Coefficient (Cd) [-]", 0.12, 0.40, 0.20, 0.01)
    frontal_area = st.slider("Frontal Area (A) [m²]", 0.8, 1.8, 1.15, 0.05)
    crr = st.slider("Rolling Resistance (Crr) [-]", 0.003, 0.020, 0.007, 0.001, format="%.3f")
    tyre_mu = st.slider("Tire Friction Coeff (μ) [-]", 0.70, 1.40, 1.15, 0.05)

with st.sidebar.expander("⚡ Electric Powertrain", expanded=False):
    motor_peak_p_kw = st.slider("Motor Peak Power [kW]", 5.0, 30.0, 12.0, 0.5)
    motor_torque_nm = st.slider("Motor Peak Torque [Nm]", 30.0, 150.0, 75.0, 5.0)
    gear_ratio = st.slider("Gear Reduction Ratio [-]", 2.0, 8.0, 4.2, 0.1)
    motor_max_rpm = st.slider("Max Motor RPM [rev/min]", 3000.0, 9000.0, 5500.0, 250.0)

with st.sidebar.expander("🔋 Battery & Regeneration", expanded=False):
    battery_v_nom = st.slider("Nominal Pack Voltage [V]", 48.0, 144.0, 96.0, 4.0)
    battery_cap_ah = st.slider("Pack Capacity [Ah]", 20.0, 100.0, 50.0, 5.0)
    initial_soc = st.slider("Initial State of Charge (SOC) [%]", 10.0, 100.0, 90.0, 5.0)
    regen_eff = st.slider("Regen Brake Efficiency [%]", 30.0, 90.0, 70.0, 5.0) / 100.0

with st.sidebar.expander("☀️ Solar Array & Environment", expanded=False):
    solar_area = st.slider("Solar PV Array Area [m²]", 1.0, 6.0, 4.0, 0.5)
    solar_eff = st.slider("PV Cell Efficiency [%]", 15.0, 30.0, 22.0, 1.0) / 100.0
    solar_irr = st.slider("Solar Irradiance [W/m²]", 0.0, 1200.0, 850.0, 50.0)

# Build configuration dict
active_config = HeliosConfig.default()
active_config.chassis.vehicle_mass = veh_mass
active_config.aero.drag_coefficient = drag_cd
active_config.aero.frontal_area = frontal_area
active_config.chassis.rolling_resistance_coeff = crr
active_config.chassis.friction_coefficient = tyre_mu
active_config.powertrain.motor_peak_power = motor_peak_p_kw * 1000.0
active_config.powertrain.motor_peak_torque = motor_torque_nm
active_config.powertrain.gear_ratio = gear_ratio
active_config.powertrain.motor_max_rpm = motor_max_rpm
active_config.battery.nominal_voltage = battery_v_nom
active_config.battery.capacity_ah = battery_cap_ah
active_config.battery.initial_soc = initial_soc
active_config.battery.regen_efficiency = regen_eff
active_config.solar.array_area = solar_area
active_config.solar.cell_efficiency = solar_eff
active_config.env.solar_irradiance = solar_irr

# Run or retrieve cached simulation
telemetry_df, summary, cfg = run_simulation(active_config.to_dict())
telemetry_mgr = TelemetryManager(telemetry_df, summary)
max_lap_time = float(telemetry_df["time_s"].iloc[-1])

# ---------------- SIMULATION PLAYBACK CONTROLS ----------------
st.sidebar.markdown("---")
st.sidebar.markdown("## ⏱️ SIMULATION CONTROLS")

# Session state initialization
if "sim_time" not in st.session_state:
    st.session_state.sim_time = 0.0
if "is_playing" not in st.session_state:
    st.session_state.is_playing = False

ctrl_col1, ctrl_col2, ctrl_col3 = st.sidebar.columns(3)
with ctrl_col1:
    if st.button("▶️ Play" if not st.session_state.is_playing else "⏸️ Pause", use_container_width=True):
        st.session_state.is_playing = not st.session_state.is_playing
with ctrl_col2:
    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.sim_time = 0.0
        st.session_state.is_playing = False
with ctrl_col3:
    if st.button("🏁 Lap End", use_container_width=True):
        st.session_state.sim_time = max_lap_time
        st.session_state.is_playing = False

playback_speed = st.sidebar.select_slider(
    "Playback Speed Multiplier",
    options=[0.5, 1.0, 2.0, 5.0, 10.0],
    value=2.0
)

# Interactive scrubber slider
selected_time = st.sidebar.slider(
    "Lap Time Scrubber [s]",
    min_value=0.0,
    max_value=max_lap_time,
    value=float(st.session_state.sim_time),
    step=0.2,
    help="Drag slider to inspect vehicle state at any point in the lap."
)

if not st.session_state.is_playing:
    st.session_state.sim_time = selected_time

# Track heatmap selection
track_color_option = st.sidebar.selectbox(
    "Track Map Metric Heatmap",
    options=["speed_kmh", "motor_elec_power_kw", "accel_y_g", "sector"],
    index=0,
    format_func=lambda x: {
        "speed_kmh": "Vehicle Speed (km/h)",
        "motor_elec_power_kw": "Motor Power (kW)",
        "accel_y_g": "Lateral Acceleration (g)",
        "sector": "Circuit Sectors (1-3)"
    }.get(x, x)
)


# ---------------- MAIN DASHBOARD LAYOUT ----------------
render_cockpit_header()

# Current instantaneous snapshot at current simulation time
current_snap = telemetry_mgr.get_snapshot_at_time(st.session_state.sim_time)

# Primary Live Telemetry HUD Bar
render_telemetry_hud(current_snap)

# Secondary Telemetry HUD Bar
render_secondary_hud(current_snap)

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# Main Visual Workspace: Left = Track Map, Right = Primary Velocity & Powertrain Traces
col_track, col_traces = st.columns([1.1, 0.9])

with col_track:
    fig_track = HeliosPlotter.create_track_map(
        telemetry_df,
        current_time_s=st.session_state.sim_time,
        color_channel=track_color_option
    )
    st.plotly_chart(fig_track, use_container_width=True)

with col_traces:
    fig_speed = HeliosPlotter.create_speed_trace(telemetry_df, current_time_s=st.session_state.sim_time)
    st.plotly_chart(fig_speed, use_container_width=True)

    fig_power = HeliosPlotter.create_powertrain_trace(telemetry_df, current_time_s=st.session_state.sim_time)
    st.plotly_chart(fig_power, use_container_width=True)


# ---------------- DETAILED TELEMETRY CHANNELS & TABS ----------------
st.markdown("### 📊 TELEMETRY ANALYSIS CHANNELS")

tab_pwr, tab_dyn, tab_nrg, tab_sum, tab_raw = st.tabs([
    "🔋 Powertrain & Battery",
    "🏎️ Vehicle Dynamics & Friction Circle",
    "☀️ Energy & Forces Balance",
    "🏁 Lap Performance Summary",
    "💾 Telemetry Export & Raw Data"
])

with tab_pwr:
    p_col1, p_col2 = st.columns(2)
    with p_col1:
        fig_batt = HeliosPlotter.create_battery_trace(telemetry_df, current_time_s=st.session_state.sim_time)
        st.plotly_chart(fig_batt, use_container_width=True)
    with p_col2:
        fig_regen = HeliosPlotter.create_regen_trace(telemetry_df, current_time_s=st.session_state.sim_time)
        st.plotly_chart(fig_regen, use_container_width=True)

with tab_dyn:
    d_col1, d_col2 = st.columns(2)
    with d_col1:
        fig_dyn = HeliosPlotter.create_dynamics_trace(telemetry_df, current_time_s=st.session_state.sim_time)
        st.plotly_chart(fig_dyn, use_container_width=True)
    with d_col2:
        fig_gg = HeliosPlotter.create_gg_diagram(telemetry_df, current_time_s=st.session_state.sim_time)
        st.plotly_chart(fig_gg, use_container_width=True)

with tab_nrg:
    e_col1, e_col2 = st.columns(2)
    with e_col1:
        fig_nrg = HeliosPlotter.create_energy_trace(telemetry_df, current_time_s=st.session_state.sim_time)
        st.plotly_chart(fig_nrg, use_container_width=True)
    with e_col2:
        fig_forces = HeliosPlotter.create_forces_trace(telemetry_df)
        st.plotly_chart(fig_forces, use_container_width=True)

with tab_sum:
    s_col1, s_col2, s_col3 = st.columns(3)
    with s_col1:
        st.markdown("#### ⏱️ Lap Timing & Splits")
        st.markdown(f"""
        - **Total Lap Time:** `{summary['lap_time_s']:.2f} s` ({summary['lap_time_s']/60:.0f}m {summary['lap_time_s']%60:.2f}s)
        - **Sector 1 Time:** `{summary['sector_1_s']:.2f} s`
        - **Sector 2 Time:** `{summary['sector_2_s']:.2f} s`
        - **Sector 3 Time:** `{summary['sector_3_s']:.2f} s`
        - **Average Lap Speed:** `{summary['avg_speed_kmh']:.1f} km/h`
        """)

    with s_col2:
        st.markdown("#### 🏎️ Kinematic Performance")
        st.markdown(f"""
        - **Maximum Velocity:** `{summary['max_speed_kmh']:.1f} km/h`
        - **Minimum Corner Apex Speed:** `{summary['min_speed_kmh']:.1f} km/h`
        - **Peak Longitudinal Accel:** `{summary['max_long_accel_mps2']:.2f} m/s²` (`{summary['max_long_accel_mps2']/9.80665:.2f} g`)
        - **Peak Braking Deceleration:** `{summary['max_braking_decel_mps2']:.2f} m/s²` (`{summary['max_braking_decel_mps2']/9.80665:.2f} g`)
        - **Peak Lateral Cornering Accel:** `{summary['max_lat_accel_mps2']:.2f} m/s²` (`{summary['max_lat_accel_g']:.2f} g`)
        """)

    with s_col3:
        st.markdown("#### ⚡ Energy & Solar Audit")
        st.markdown(f"""
        - **Gross Discharged Energy:** `{summary['energy_consumed_kwh']:.3f} kWh`
        - **Regenerated Braking Energy:** `{summary['energy_regenerated_kwh']:.3f} kWh`
        - **Solar PV Energy Harvested:** `{summary['solar_energy_harvested_kwh']:.3f} kWh`
        - **Net Pack Energy Consumed:** `{summary['net_energy_kwh']:.3f} kWh`
        - **Specific Energy Efficiency:** `{summary['efficiency_wh_km']:.1f} Wh/km`
        - **Initial Battery SOC:** `{summary['initial_soc_pct']:.1f} %`
        - **Final Battery SOC:** `{summary['final_soc_pct']:.2f} %` (`{summary['soc_delta_pct']:+.2f} %`)
        """)

with tab_raw:
    st.markdown("#### 💾 Telemetry Stream")
    st.dataframe(
        telemetry_df[[
            "time_s", "distance_m", "sector", "speed_kmh", "motor_rpm",
            "motor_elec_power_kw", "solar_power_w", "regen_power_kw",
            "battery_voltage_v", "battery_current_a", "battery_soc_pct",
            "accel_x_g", "accel_y_g", "net_energy_kwh"
        ]].round(3),
        height=320,
        use_container_width=True
    )

    csv_data = telemetry_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Full Telemetry CSV",
        data=csv_data,
        file_name="helios_kari_speedway_telemetry.csv",
        mime="text/csv"
    )

# ---------------- ANIMATION PLAYBACK LOOP ----------------
if st.session_state.is_playing:
    step_dt = 0.5 * playback_speed
    if st.session_state.sim_time + step_dt >= max_lap_time:
        st.session_state.sim_time = max_lap_time
        st.session_state.is_playing = False
    else:
        st.session_state.sim_time += step_dt
    time.sleep(0.08)
    st.rerun()

