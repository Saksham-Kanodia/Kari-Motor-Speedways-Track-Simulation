"""
Lap Simulator & Velocity Profile Engine
Solves the quasi-steady state forward-backward acceleration-braking passes
and integrates physical dynamics for a complete lap around Kari Motor Speedway.
"""

from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from config import HeliosConfig
from physics_engine.vehicle import VehiclePhysics
from .track import KariTrack


class LapSimulator:
    """
    Two-pass numerical velocity profiler and time-domain integrator.
    """
    def __init__(self, config: HeliosConfig = None, track: KariTrack = None):
        self.cfg = config or HeliosConfig.default()
        self.track = track or KariTrack()
        self.vehicle = VehiclePhysics(self.cfg)

    def compute_speed_profile(self) -> np.ndarray:
        """
        Calculates the physics-limited velocity profile around the circuit
        using forward acceleration and backward braking passes.
        """
        track_df = self.track.get_track_data()
        n = len(track_df)
        distances = track_df["distance_m"].values
        curvatures = track_df["curvature_rad_m"].values

        # 1. Cornering speed limit at every point
        v_corner = np.zeros(n)
        for i in range(n):
            v_corner[i] = self.vehicle.dynamics.compute_max_cornering_speed(curvatures[i])

        # 2. Forward pass (Acceleration limited by motor torque/power, aero drag, and grip)
        v_fwd = np.zeros(n)
        # Seed start speed with T14 exit cornering speed
        v_fwd[0] = min(v_corner[0], 18.0) # ~65 km/h flying lap start

        for i in range(n - 1):
            ds = distances[i + 1] - distances[i]
            v_curr = v_fwd[i]
            a_max = self.vehicle.compute_max_acceleration(v_curr, curvatures[i])
            # v^2 = u^2 + 2 * a * ds
            v_next_sq = max(0.1, v_curr**2 + 2.0 * a_max * ds)
            v_next = np.sqrt(v_next_sq)
            v_fwd[i + 1] = min(v_corner[i + 1], v_next)

        # 3. Backward pass (Braking limited by service brake, aero drag, and grip)
        v_bwd = np.copy(v_fwd)
        for i in range(n - 1, 0, -1):
            ds = distances[i] - distances[i - 1]
            v_curr = v_bwd[i]
            a_decel = self.vehicle.compute_max_deceleration(v_curr, curvatures[i])
            # v_prev^2 = v_curr^2 + 2 * a_decel * ds
            v_prev_sq = max(0.1, v_curr**2 + 2.0 * a_decel * ds)
            v_prev = np.sqrt(v_prev_sq)
            v_bwd[i - 1] = min(v_bwd[i - 1], v_prev)

        # 4. Final profile: element-wise minimum of forward and backward passes
        v_profile = np.minimum(v_fwd, v_bwd)

        # 5. Cyclic smoothing for closed track loop continuity
        # Repeat forward-backward pass once with converged boundary to guarantee perfect loop
        v_fwd[0] = v_profile[-1]
        for i in range(n - 1):
            ds = distances[i + 1] - distances[i]
            a_max = self.vehicle.compute_max_acceleration(v_fwd[i], curvatures[i])
            v_fwd[i + 1] = min(v_corner[i + 1], np.sqrt(max(0.1, v_fwd[i]**2 + 2.0 * a_max * ds)))

        v_bwd[-1] = min(v_fwd[-1], v_profile[0])
        for i in range(n - 1, 0, -1):
            ds = distances[i] - distances[i - 1]
            a_decel = self.vehicle.compute_max_deceleration(v_bwd[i], curvatures[i])
            v_bwd[i - 1] = min(v_bwd[i - 1], np.sqrt(max(0.1, v_bwd[i]**2 + 2.0 * a_decel * ds)))

        v_final = np.minimum(v_fwd, v_bwd)
        return v_final

    def run_lap(self) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Executes complete numerical lap integration and compiles telemetry stream.
        """
        track_df = self.track.get_track_data()
        n = len(track_df)
        distances = track_df["distance_m"].values
        curvatures = track_df["curvature_rad_m"].values
        x_pts = track_df["x_m"].values
        y_pts = track_df["y_m"].values
        sectors = track_df["sector"].values

        v_profile = self.compute_speed_profile()

        # Reset vehicle battery and energy counters
        self.vehicle.battery.reset()
        self.vehicle.solar_energy_harvested_j = 0.0

        telemetry_rows = []
        current_time = 0.0

        for i in range(n):
            dist = distances[i]
            v = v_profile[i]
            k = curvatures[i]
            sec = sectors[i]
            x = x_pts[i]
            y = y_pts[i]

            if i < n - 1:
                ds = distances[i + 1] - distances[i]
                v_next = v_profile[i + 1]
                v_avg = max(0.5 * (v + v_next), 0.5)
                dt = ds / v_avg
                # Acceleration: a = (v_next^2 - v^2) / (2 * ds)
                demanded_a = (v_next**2 - v**2) / (2.0 * ds)
            else:
                # Last segment wrap-around
                ds = distances[-1] - distances[-2]
                dt = ds / max(v, 0.5)
                demanded_a = (v_profile[0]**2 - v**2) / (2.0 * ds)

            # Step physical systems
            phys_step = self.vehicle.step(
                speed_mps=v,
                demanded_accel_mps2=demanded_a,
                dt=dt,
                curvature=k
            )

            # Record telemetry point
            row = {
                "time_s": current_time,
                "distance_m": dist,
                "x_m": x,
                "y_m": y,
                "sector": sec,
                "speed_mps": v,
                "speed_kmh": v * 3.6,
                "accel_x_mps2": phys_step["accel_x"],
                "accel_y_mps2": phys_step["accel_y"],
                "accel_x_g": phys_step["accel_x"] / 9.80665,
                "accel_y_g": phys_step["accel_y"] / 9.80665,
                "curvature": k,
                "f_drive_n": phys_step["f_drive"],
                "f_drag_n": phys_step["f_drag"],
                "f_rolling_n": phys_step["f_rolling"],
                "f_brake_n": phys_step["f_brake"],
                "f_net_n": phys_step["f_net"],
                "motor_rpm": phys_step["motor_rpm"],
                "motor_torque_nm": phys_step["motor_torque"],
                "motor_mech_power_kw": phys_step["motor_mech_power_kw"],
                "motor_elec_power_kw": phys_step["motor_elec_power_kw"],
                "motor_efficiency": phys_step["motor_efficiency"],
                "solar_power_w": phys_step["solar_power_w"],
                "solar_energy_kwh": phys_step["solar_energy_harvested_kwh"],
                "regen_power_kw": phys_step["regen_power_kw"],
                "battery_voltage_v": phys_step["battery_voltage"],
                "battery_current_a": phys_step["battery_current"],
                "battery_power_kw": phys_step["battery_power_kw"],
                "battery_soc_pct": phys_step["battery_soc"],
                "energy_consumed_kwh": phys_step["energy_consumed_kwh"],
                "energy_regenerated_kwh": phys_step["energy_regenerated_kwh"],
                "net_energy_kwh": phys_step["net_energy_kwh"]
            }
            telemetry_rows.append(row)
            current_time += dt

        telemetry_df = pd.DataFrame(telemetry_rows)

        # Performance summary metrics
        total_lap_time = telemetry_df["time_s"].iloc[-1]
        max_speed = telemetry_df["speed_kmh"].max()
        min_speed = telemetry_df["speed_kmh"].min()
        avg_speed = (self.track.total_length_m / total_lap_time) * 3.6
        energy_discharged = telemetry_df["energy_consumed_kwh"].iloc[-1]
        energy_recovered = telemetry_df["energy_regenerated_kwh"].iloc[-1]
        solar_harvested = telemetry_df["solar_energy_kwh"].iloc[-1]
        net_energy = telemetry_df["net_energy_kwh"].iloc[-1]
        initial_soc = self.cfg.battery.initial_soc
        final_soc = telemetry_df["battery_soc_pct"].iloc[-1]
        max_long_accel = telemetry_df["accel_x_mps2"].max()
        max_braking_decel = abs(telemetry_df["accel_x_mps2"].min())
        max_lat_accel = np.abs(telemetry_df["accel_y_mps2"]).max()

        # Sector split times
        s1_time = telemetry_df[telemetry_df["sector"] == 1]["time_s"].max()
        s2_time = telemetry_df[telemetry_df["sector"] == 2]["time_s"].max() - s1_time
        s3_time = total_lap_time - (s1_time + s2_time)

        # Energy consumption rate (Wh/km)
        total_dist_km = self.track.total_length_m / 1000.0
        efficiency_wh_km = (net_energy * 1000.0) / total_dist_km

        summary = {
            "lap_time_s": total_lap_time,
            "sector_1_s": s1_time,
            "sector_2_s": s2_time,
            "sector_3_s": s3_time,
            "max_speed_kmh": max_speed,
            "min_speed_kmh": min_speed,
            "avg_speed_kmh": avg_speed,
            "max_long_accel_mps2": max_long_accel,
            "max_braking_decel_mps2": max_braking_decel,
            "max_lat_accel_mps2": max_lat_accel,
            "max_lat_accel_g": max_lat_accel / 9.80665,
            "energy_consumed_kwh": energy_discharged,
            "energy_regenerated_kwh": energy_recovered,
            "solar_energy_harvested_kwh": solar_harvested,
            "net_energy_kwh": net_energy,
            "efficiency_wh_km": efficiency_wh_km,
            "initial_soc_pct": initial_soc,
            "final_soc_pct": final_soc,
            "soc_delta_pct": final_soc - initial_soc
        }

        return telemetry_df, summary

