"""
Vehicle Lateral Dynamics & Cornering Physics Model
Calculates cornering speed envelopes, lateral acceleration, tyre load transfer,
and combined acceleration limits via the friction circle.
"""

import numpy as np
from config import ChassisParameters, EnvironmentalParameters


class LateralDynamics:
    """
    Models cornering kinematics, tyre-road adhesion limits, and load transfer.
    """
    def __init__(self, chassis: ChassisParameters, env: EnvironmentalParameters):
        self.c = chassis
        self.env = env
        # Wheel track width assumption (m) for single-seater solar car
        self.track_width = 1.25

    def compute_lateral_acceleration(self, speed_mps: float, curvature: float) -> float:
        """
        Computes lateral acceleration: a_y = v^2 * curvature (m/s^2).
        Sign matches turn direction (+ for left, - for right).
        """
        return float((speed_mps ** 2) * curvature)

    def compute_max_cornering_speed(self, curvature: float, safety_factor: float = 0.98) -> float:
        """
        Calculates maximum permissible cornering speed without tyre breakaway:
        v_max = sqrt( (mu * g * safety_factor) / |curvature| )
        For straight sections (|curvature| -> 0), returns a high ceiling (e.g. 150 km/h).
        """
        abs_k = abs(curvature)
        if abs_k < 1e-4:
            # Virtually straight: return ceiling speed well above vehicle capability
            return 60.0  # ~216 km/h ceiling

        max_ay = self.c.friction_coefficient * self.env.gravity * safety_factor
        v_max = np.sqrt(max_ay / abs_k)
        return float(v_max)

    def compute_lateral_load_transfer(self, lateral_accel_mps2: float) -> dict:
        """
        Computes dynamic lateral weight transfer across wheels during cornering:
        Delta_Fz = (m * a_y * h_cg) / track_width
        """
        delta_fz = (self.c.vehicle_mass * abs(lateral_accel_mps2) * self.c.cog_height) / self.track_width
        static_wheel_load = (self.c.vehicle_mass * self.env.gravity) / 4.0 # 4 wheels

        inner_wheel_load = max(0.0, static_wheel_load - delta_fz / 2.0)
        outer_wheel_load = static_wheel_load + delta_fz / 2.0

        return {
            "delta_fz_n": float(delta_fz),
            "inner_wheel_load_n": float(inner_wheel_load),
            "outer_wheel_load_n": float(outer_wheel_load)
        }

    def compute_available_longitudinal_accel(self, current_lat_accel_mps2: float) -> float:
        """
        Uses Kamm's friction circle to determine the remaining longitudinal traction/braking
        capacity when tyres are sustaining lateral cornering forces:
        (a_x / a_max)^2 + (a_y / a_max)^2 <= 1.0
        """
        a_max = self.c.friction_coefficient * self.env.gravity
        lat_ratio = min(1.0, abs(current_lat_accel_mps2) / max(a_max, 1e-3))
        # Remaining longitudinal grip ratio
        remaining_ratio = np.sqrt(max(0.0, 1.0 - (lat_ratio ** 2)))
        return float(a_max * remaining_ratio)

