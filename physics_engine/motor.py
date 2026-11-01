"""
Electric Motor & Drivetrain Physics Model
Simulates the performance, torque curves, and power limits of a high-efficiency EV powertrain.
"""

import numpy as np
from config import PowertrainParameters, ChassisParameters


class ElectricMotor:
    """
    Physics-based Permanent Magnet Synchronous Motor (PMSM) or BLDC motor model.
    Accounts for torque limits, constant power field-weakening regime, and rotational cut-off.
    """
    def __init__(self, powertrain: PowertrainParameters, chassis: ChassisParameters):
        self.p = powertrain
        self.c = chassis

        # Base angular velocity where motor transitions from constant torque to constant power
        # P_peak = T_max * omega_base => omega_base = P_peak / T_max
        self.omega_base = self.p.motor_peak_power / max(self.p.motor_peak_torque, 1e-3)
        self.rpm_base = self.omega_base * 60.0 / (2.0 * np.pi)

    def vehicle_speed_to_motor_rpm(self, speed_mps: float) -> float:
        """
        Converts vehicle translational speed (m/s) to motor rotational speed (RPM).
        """
        if speed_mps <= 0.0:
            return 0.0
        wheel_omega = speed_mps / self.c.wheel_radius  # rad/s
        motor_omega = wheel_omega * self.p.gear_ratio   # rad/s
        rpm = motor_omega * 60.0 / (2.0 * np.pi)
        return float(min(rpm, self.p.motor_max_rpm * 1.2)) # Allow small overrun check

    def motor_rpm_to_vehicle_speed(self, rpm: float) -> float:
        """
        Converts motor RPM to vehicle linear speed (m/s).
        """
        motor_omega = rpm * (2.0 * np.pi) / 60.0
        wheel_omega = motor_omega / self.p.gear_ratio
        return float(wheel_omega * self.c.wheel_radius)

    def get_max_motor_torque(self, rpm: float) -> float:
        """
        Returns maximum achievable motor torque (Nm) at given RPM.
        """
        if rpm <= 0.0:
            return self.p.motor_peak_torque
        if rpm >= self.p.motor_max_rpm:
            return 0.0

        omega = rpm * (2.0 * np.pi) / 60.0

        if omega <= self.omega_base:
            # Constant torque region
            return self.p.motor_peak_torque
        else:
            # Constant power (field weakening) region
            torque_power_limited = self.p.motor_peak_power / omega
            return float(min(torque_power_limited, self.p.motor_peak_torque))

    def get_tractive_force(self, speed_mps: float, throttle: float = 1.0) -> float:
        """
        Computes tractive driving force (N) delivered at wheels for a given vehicle speed.
        throttle in range [0.0, 1.0].
        """
        throttle = np.clip(throttle, 0.0, 1.0)
        rpm = self.vehicle_speed_to_motor_rpm(speed_mps)
        max_torque = self.get_max_motor_torque(rpm)
        demanded_torque = max_torque * throttle

        # Wheel torque = Motor torque * Gear ratio * Drivetrain efficiency
        wheel_torque = demanded_torque * self.p.gear_ratio * self.p.drivetrain_efficiency
        tractive_force = wheel_torque / self.c.wheel_radius
        return float(tractive_force)

    def calculate_operating_point(self, speed_mps: float, tractive_force: float) -> dict:
        """
        Calculates exact motor operating telemetry for a given speed and tractive force demand.
        """
        rpm = self.vehicle_speed_to_motor_rpm(speed_mps)
        omega = rpm * (2.0 * np.pi) / 60.0

        # Back-calculate required wheel torque and motor torque
        wheel_torque = tractive_force * self.c.wheel_radius
        if self.p.gear_ratio > 0 and self.p.drivetrain_efficiency > 0:
            motor_torque = wheel_torque / (self.p.gear_ratio * self.p.drivetrain_efficiency)
        else:
            motor_torque = 0.0

        mech_power = motor_torque * omega # Watts

        # Motor efficiency modeling: base efficiency with slight droop at low load/extreme speed
        if mech_power > 0:
            # Motoring
            efficiency = self.p.motor_base_efficiency
            elec_power = mech_power / max(efficiency, 0.5)
        else:
            # Stationary or zero torque
            efficiency = self.p.motor_base_efficiency
            elec_power = 0.0

        return {
            "rpm": float(rpm),
            "torque_nm": float(motor_torque),
            "mech_power_w": float(mech_power),
            "elec_power_w": float(elec_power),
            "efficiency": float(efficiency)
        }

