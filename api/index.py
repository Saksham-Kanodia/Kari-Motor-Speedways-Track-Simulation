"""
FastAPI Serverless Backend for HELIOS Digital Twin on Vercel
Exposes endpoints for circuit geometry, default lap telemetry, and on-demand physics simulations.
"""

import os
import sys
from typing import Dict, Any, Optional

# Add project root to sys.path so physics_engine, simulation, and config are importable
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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

# Initialize FastAPI application
app = FastAPI(
    title="HELIOS — Physics-Based Solar EV Digital Twin API",
    description="High-fidelity vehicle dynamics, battery electrochemistry, and Kari Motor Speedway lap simulation API",
    version="1.0.0"
)

# Enable CORS for local development and Vercel frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global cached track instance
_KARI_TRACK: Optional[KariTrack] = None
_DEFAULT_TELEMETRY = None
_DEFAULT_SUMMARY = None


def get_track() -> KariTrack:
    global _KARI_TRACK
    if _KARI_TRACK is None:
        _KARI_TRACK = KariTrack(resolution_m=2.0, data_dir=os.path.join(ROOT_DIR, "data"))
    return _KARI_TRACK


def get_default_results():
    global _DEFAULT_TELEMETRY, _DEFAULT_SUMMARY
    if _DEFAULT_TELEMETRY is None or _DEFAULT_SUMMARY is None:
        track = get_track()
        cfg = HeliosConfig.default()
        sim = LapSimulator(config=cfg, track=track)
        df, summary = sim.run_lap()
        _DEFAULT_TELEMETRY = df
        _DEFAULT_SUMMARY = summary
    return _DEFAULT_TELEMETRY, _DEFAULT_SUMMARY


class SimulationRequest(BaseModel):
    vehicle_mass: float = Field(320.0, ge=180.0, le=600.0, description="Total mass [kg]")
    drag_coefficient: float = Field(0.20, ge=0.10, le=0.50, description="Aerodynamic Cd")
    frontal_area: float = Field(1.15, ge=0.7, le=2.5, description="Frontal area [m^2]")
    rolling_resistance_coeff: float = Field(0.007, ge=0.002, le=0.030, description="Rolling resistance Crr")
    friction_coefficient: float = Field(1.15, ge=0.6, le=1.6, description="Tyre-road friction mu")
    motor_peak_power_kw: float = Field(12.0, ge=4.0, le=35.0, description="Peak motor power [kW]")
    motor_peak_torque_nm: float = Field(75.0, ge=20.0, le=180.0, description="Peak motor torque [Nm]")
    gear_ratio: float = Field(4.2, ge=2.0, le=9.0, description="Gear reduction ratio")
    battery_nominal_voltage: float = Field(96.0, ge=48.0, le=150.0, description="Nominal battery voltage [V]")
    battery_capacity_ah: float = Field(50.0, ge=15.0, le=120.0, description="Pack capacity [Ah]")
    initial_soc_pct: float = Field(90.0, ge=10.0, le=100.0, description="Initial SOC [%]")
    regen_efficiency_pct: float = Field(70.0, ge=20.0, le=95.0, description="Regen braking efficiency [%]")
    solar_irradiance_wm2: float = Field(850.0, ge=0.0, le=1200.0, description="Solar irradiance [W/m^2]")
    solar_array_area_m2: float = Field(4.0, ge=1.0, le=7.0, description="Solar array area [m^2]")


@app.get("/api/health")
def health_check():
    """Health check endpoint for Vercel deployment verification."""
    return {
        "status": "online",
        "service": "HELIOS Physics Engine & Lap Simulator",
        "circuit": "Kari Motor Speedway, Coimbatore",
        "circuit_length_m": 2120.0,
        "turns_count": 14
    }


@app.get("/api/track")
def get_circuit_data():
    """Returns the Kari Motor Speedway centerline coordinates, curvature, and sector markers."""
    track = get_track()
    df = track.get_track_data()
    return {
        "circuit_name": "Kari Motor Speedway",
        "location": "Coimbatore, Tamil Nadu, India",
        "total_length_m": track.total_length_m,
        "points_count": len(df),
        "x": df["x_m"].round(2).tolist(),
        "y": df["y_m"].round(2).tolist(),
        "distance": df["distance_m"].round(2).tolist(),
        "curvature": df["curvature_rad_m"].round(5).tolist(),
        "sector": df["sector"].tolist()
    }


@app.get("/api/default-lap")
def get_default_lap_telemetry():
    """Returns the baseline lap simulation telemetry stream and performance summary."""
    df, summary = get_default_results()
    clean_summary = {k: float(v) if hasattr(v, "__float__") else v for k, v in summary.items()}
    return {
        "summary": clean_summary,
        "telemetry": {
            "time_s": df["time_s"].round(3).tolist(),
            "distance_m": df["distance_m"].round(2).tolist(),
            "x_m": df["x_m"].round(2).tolist(),
            "y_m": df["y_m"].round(2).tolist(),
            "sector": df["sector"].tolist(),
            "speed_kmh": df["speed_kmh"].round(2).tolist(),
            "motor_rpm": df["motor_rpm"].round(0).tolist(),
            "motor_elec_power_kw": df["motor_elec_power_kw"].round(2).tolist(),
            "battery_soc_pct": df["battery_soc_pct"].round(2).tolist(),
            "battery_current_a": df["battery_current_a"].round(2).tolist(),
            "battery_voltage_v": df["battery_voltage_v"].round(2).tolist(),
            "battery_power_kw": df["battery_power_kw"].round(2).tolist(),
            "accel_x_g": df["accel_x_g"].round(3).tolist(),
            "accel_y_g": df["accel_y_g"].round(3).tolist(),
            "solar_power_w": df["solar_power_w"].round(1).tolist(),
            "regen_power_kw": df["regen_power_kw"].round(2).tolist(),
            "net_energy_kwh": df["net_energy_kwh"].round(4).tolist(),
            "energy_consumed_kwh": df["energy_consumed_kwh"].round(4).tolist(),
            "energy_regenerated_kwh": df["energy_regenerated_kwh"].round(4).tolist(),
            "solar_energy_kwh": df["solar_energy_kwh"].round(4).tolist()
        }
    }


@app.post("/api/simulate")
def run_custom_simulation(req: SimulationRequest):
    """
    Executes a new physics lap simulation with custom vehicle parameters.
    """
    try:
        cfg = HeliosConfig(
            env=EnvironmentalParameters(solar_irradiance=req.solar_irradiance_wm2),
            aero=AerodynamicParameters(
                drag_coefficient=req.drag_coefficient,
                frontal_area=req.frontal_area
            ),
            chassis=ChassisParameters(
                vehicle_mass=req.vehicle_mass,
                rolling_resistance_coeff=req.rolling_resistance_coeff,
                friction_coefficient=req.friction_coefficient
            ),
            powertrain=PowertrainParameters(
                motor_peak_power=req.motor_peak_power_kw * 1000.0,
                motor_peak_torque=req.motor_peak_torque_nm,
                gear_ratio=req.gear_ratio
            ),
            battery=BatteryParameters(
                nominal_voltage=req.battery_nominal_voltage,
                capacity_ah=req.battery_capacity_ah,
                initial_soc=req.initial_soc_pct,
                regen_efficiency=req.regen_efficiency_pct / 100.0
            ),
            solar=SolarArrayParameters(
                array_area=req.solar_array_area_m2
            ),
            track=TrackParameters()
        )

        track = get_track()
        sim = LapSimulator(config=cfg, track=track)
        df, summary = sim.run_lap()

        clean_summary = {k: float(v) if hasattr(v, "__float__") else v for k, v in summary.items()}

        return {
            "summary": clean_summary,
            "telemetry": {
                "time_s": df["time_s"].round(3).tolist(),
                "distance_m": df["distance_m"].round(2).tolist(),
                "x_m": df["x_m"].round(2).tolist(),
                "y_m": df["y_m"].round(2).tolist(),
                "sector": df["sector"].tolist(),
                "speed_kmh": df["speed_kmh"].round(2).tolist(),
                "motor_rpm": df["motor_rpm"].round(0).tolist(),
                "motor_elec_power_kw": df["motor_elec_power_kw"].round(2).tolist(),
                "battery_soc_pct": df["battery_soc_pct"].round(2).tolist(),
                "battery_current_a": df["battery_current_a"].round(2).tolist(),
                "battery_voltage_v": df["battery_voltage_v"].round(2).tolist(),
                "battery_power_kw": df["battery_power_kw"].round(2).tolist(),
                "accel_x_g": df["accel_x_g"].round(3).tolist(),
                "accel_y_g": df["accel_y_g"].round(3).tolist(),
                "solar_power_w": df["solar_power_w"].round(1).tolist(),
                "regen_power_kw": df["regen_power_kw"].round(2).tolist(),
                "net_energy_kwh": df["net_energy_kwh"].round(4).tolist(),
                "energy_consumed_kwh": df["energy_consumed_kwh"].round(4).tolist(),
                "energy_regenerated_kwh": df["energy_regenerated_kwh"].round(4).tolist(),
                "solar_energy_kwh": df["solar_energy_kwh"].round(4).tolist()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

