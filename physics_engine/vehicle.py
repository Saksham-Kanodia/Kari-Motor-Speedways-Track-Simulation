"""
Complete Vehicle Longitudinal & Powertrain Integration Model
Implements Newton's second law for the vehicle chassis with aerodynamic drag,
rolling resistance, electric traction, regenerative braking, and solar PV harvesting.
"""

from dataclasses import dataclass
import numpy as np
from config import HeliosConfig
from .motor import ElectricMotor
from .battery import BatteryPack, BatteryState
from .dynamics import LateralDynamics


@dataclass
class TelemetrySnapshot:
    time_s: float
    distance_m: float
    speed_mps: float
    speed_kmh: float
    accel_longitudinal_mps2: float
    accel_lateral_mps2: float
    motor_rpm: float
    motor_torque_nm: float
    motor_power_kw: float
    motor_efficiency: float
    solar_power_w: float
    battery_voltage_v: float
    battery_current_a: float
    battery_power_kw: float
    battery_soc_pct: float
    energy_consumed_kwh: float
    energy_regenerated_kwh: float
    solar_energy_harvested_kwh: float
    net_energy_kwh: float
    f_drive_n: float
    f_drag_n: float
    f_rolling_n: float
    f_brake_n: float
    f_net_n: float
    curvature: float
    track_x: float
    track_y: float
    sector: int


class VehiclePhysics:
    """
    Core Physics Digital Twin for the HELIOS Solar EV.
    """
    def __init__(self, config: HeliosConfig):
        self.cfg = config
        self.motor = ElectricMotor(config.powertrain, config.chassis)
        self.battery = BatteryPack(config.battery)
        self.dynamics = LateralDynamics(config.chassis, config.env)
        self.solar_energy_harvested_j = 0.0

    def compute_aerodynamic_drag(self, speed_mps: float) -> float:
        """
        F_drag = 0.5 * rho * Cd * A * v^2
        Opposes direction of motion.
        """
        v = max(0.0, speed_mps)
        return float(0.5 * self.cfg.env.air_density * self.cfg.aero.drag_coefficient * self.cfg.aero.frontal_area * (v ** 2))

    def compute_rolling_resistance(self, speed_mps: float, incline_rad: float = 0.0) -> float:
        """
        F_rolling = Crr * m * g * cos(theta)
        Acts only when vehicle is moving or under drive force.
        """
        normal_force = self.cfg.chassis.vehicle_mass * self.cfg.env.gravity * np.cos(incline_rad)
        f_rr = self.cfg.chassis.rolling_resistance_coeff * normal_force
        if speed_mps <= 0.001:
            return 0.0
        return float(f_rr)

    def compute_gradient_resistance(self, incline_rad: float = 0.0) -> float:
        """
        F_gradient = m * g * sin(theta)
        """
        return float(self.cfg.chassis.vehicle_mass * self.cfg.env.gravity * np.sin(incline_rad))

    def compute_solar_power(self) -> float:
        """
        P_solar = A_pv * eta_pv * eta_mppt * Solar_Irradiance (Watts)
        Continuous clean energy generated directly from on-board solar arrays.
        """
        s = self.cfg.solar
        p_solar = s.array_area * s.cell_efficiency * s.mppt_efficiency * self.cfg.env.solar_irradiance
        return float(p_solar)

    def compute_max_acceleration(self, speed_mps: float, curvature: float = 0.0) -> float:
        """
        Calculates maximum possible forward acceleration at given speed,
        accounting for motor torque/power limit, aerodynamic drag, rolling resistance,
        and lateral tyre grip reservation (friction ellipse).
        """
        # Aerodynamic and rolling resistive forces
        f_drag = self.compute_aerodynamic_drag(speed_mps)
        f_rr = self.compute_rolling_resistance(speed_mps)

        # Maximum motor tractive force
        f_tractive_motor = self.motor.get_tractive_force(speed_mps, throttle=1.0)

        # Check friction circle longitudinal limit from cornering lateral accel
        a_y = self.dynamics.compute_lateral_acceleration(speed_mps, curvature)
        a_x_max_grip = self.dynamics.compute_available_longitudinal_accel(a_y)
        f_grip_max = a_x_max_grip * self.cfg.chassis.vehicle_mass

        f_drive = min(f_tractive_motor, f_grip_max)
        f_net = f_drive - f_drag - f_rr
        a_net = f_net / self.cfg.chassis.vehicle_mass
        return float(a_net)

    def compute_max_deceleration(self, speed_mps: float, curvature: float = 0.0) -> float:
        """
        Calculates maximum achievable deceleration (positive magnitude) during braking,
        accounting for mechanical braking force, regenerative braking, aero drag,
        rolling resistance, and tyre friction circle.
        """
        f_drag = self.compute_aerodynamic_drag(speed_mps)
        f_rr = self.compute_rolling_resistance(speed_mps)

        # Tyre friction limit
        a_y = self.dynamics.compute_lateral_acceleration(speed_mps, curvature)
        a_x_max_grip = self.dynamics.compute_available_longitudinal_accel(a_y)
        f_grip_max = a_x_max_grip * self.cfg.chassis.vehicle_mass

        # Total braking capability is bounded by service brake and tyre grip
        f_braking_max = min(self.cfg.chassis.max_braking_force, f_grip_max)

        # Total deceleration force = F_braking + F_drag + F_rolling
        total_stopping_force = f_braking_max + f_drag + f_rr
        decel = total_stopping_force / self.cfg.chassis.vehicle_mass
        return float(decel)

    def step(
        self,
        speed_mps: float,
        demanded_accel_mps2: float,
        dt: float,
        curvature: float = 0.0,
        incline_rad: float = 0.0
    ) -> dict:
        """
        Executes one physics time step:
        - Resolves required forces
        - Evaluates motor or braking operating regime
        - Computes regenerative power recovery
        - Updates solar power input
        - Advances battery electrochemistry
        - Returns full snapshot dictionary
        """
        m = self.cfg.chassis.vehicle_mass
        f_drag = self.compute_aerodynamic_drag(speed_mps)
        f_rr = self.compute_rolling_resistance(speed_mps, incline_rad)
        f_grad = self.compute_gradient_resistance(incline_rad)

        solar_p = self.compute_solar_power()
        self.solar_energy_harvested_j += solar_p * dt

        f_net_target = m * demanded_accel_mps2
        # F_net = F_drive - F_drag - F_rolling - F_grad - F_brake
        # If f_net_target > -(f_drag + f_rr + f_grad), we need driving force
        f_req = f_net_target + f_drag + f_rr + f_grad

        if f_req >= 0:
            # ACCELERATION / MOTORING REGIME
            f_drive_available = self.motor.get_tractive_force(speed_mps, throttle=1.0)
            f_drive = float(min(f_req, f_drive_available))
            f_brake = 0.0
            motor_op = self.motor.calculate_operating_point(speed_mps, f_drive)
            motor_elec_p = motor_op["elec_power_w"]
            regen_p = 0.0

            # Net electrical demand on battery = Motor Electrical Demand - Solar Generation
            net_battery_p = motor_elec_p - solar_p
        else:
            # BRAKING / DECELERATION REGIME
            f_drive = 0.0
            motor_op = self.motor.calculate_operating_point(speed_mps, 0.0)
            f_brake_needed = -f_req
            f_brake = float(min(f_brake_needed, self.cfg.chassis.max_braking_force))

            # Regenerative braking recovery
            # Mechanical braking power = F_brake * speed
            p_brake_mech = f_brake * speed_mps
            # Regenerated electrical power
            regen_p = min(p_brake_mech * self.cfg.battery.regen_efficiency, self.cfg.battery.max_regen_power)
            # Battery power target: negative means power entering battery (charging)
            net_battery_p = - (regen_p + solar_p)

        # Update battery state
        batt_state = self.battery.step(net_battery_p, dt)

        # Resulting net force and actual acceleration
        f_net_actual = f_drive - f_drag - f_rr - f_grad - f_brake
        actual_accel = f_net_actual / m
        lat_accel = self.dynamics.compute_lateral_acceleration(speed_mps, curvature)

        return {
            "accel_x": float(actual_accel),
            "accel_y": float(lat_accel),
            "f_drive": float(f_drive),
            "f_drag": float(f_drag),
            "f_rolling": float(f_rr),
            "f_brake": float(f_brake),
            "f_net": float(f_net_actual),
            "motor_rpm": motor_op["rpm"],
            "motor_torque": motor_op["torque_nm"],
            "motor_mech_power_kw": motor_op["mech_power_w"] / 1000.0,
            "motor_elec_power_kw": motor_op["elec_power_w"] / 1000.0,
            "motor_efficiency": motor_op["efficiency"],
            "solar_power_w": solar_p,
            "solar_energy_harvested_kwh": self.solar_energy_harvested_j / 3.6e6,
            "regen_power_kw": regen_p / 1000.0,
            "battery_voltage": batt_state.terminal_voltage,
            "battery_current": batt_state.current_a,
            "battery_power_kw": batt_state.power_w / 1000.0,
            "battery_soc": batt_state.soc_pct,
            "energy_consumed_kwh": batt_state.energy_consumed_j / 3.6e6,
            "energy_regenerated_kwh": batt_state.energy_regenerated_j / 3.6e6,
            "net_energy_kwh": batt_state.net_energy_kwh
        }

