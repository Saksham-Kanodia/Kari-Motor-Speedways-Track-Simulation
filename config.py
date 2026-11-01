"""
HELIOS Solar Electric Vehicle Configuration Module
Centralized vehicle specifications, environmental constants, and simulation parameters.

Engineering Note:
Parameters are clearly partitioned into:
- Physical Constants (Standard SI)
- Provisional Engineering Assumptions (Customizable for Solar EV prototypes)
- Kari Motor Speedway Circuit Parameters
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class EnvironmentalParameters:
    air_density: float = 1.225         # kg/m^3 (Standard air density at sea level, 15°C)
    gravity: float = 9.80665           # m/s^2 (Standard gravitational acceleration)
    ambient_temperature: float = 30.0  # °C (Typical daytime ambient in Coimbatore, India)
    solar_irradiance: float = 850.0    # W/m^2 (Typical direct normal + diffuse irradiance)


@dataclass
class AerodynamicParameters:
    drag_coefficient: float = 0.20     # Cd [-] (Provisional aerodynamic assumption for streamlined solar EV)
    frontal_area: float = 1.15         # A [m^2] (Provisional assumption based on single-seater solar car profile)


@dataclass
class ChassisParameters:
    vehicle_mass: float = 320.0        # m [kg] (Vehicle curb weight ~245kg + 75kg driver)
    wheel_radius: float = 0.28         # rw [m] (Standard low-rolling resistance solar racing tyre, e.g. 95/80-16)
    rolling_resistance_coeff: float = 0.007  # Crr [-] (Low rolling resistance solar tyre assumption)
    wheelbase: float = 2.05            # L [m] (Distance between front and rear axles)
    cog_height: float = 0.35           # hcg [m] (Centre of gravity height above ground)
    friction_coefficient: float = 1.15 # mu [-] (Dry asphalt tyre-road grip coefficient at Kari Motor Speedway)
    max_braking_force: float = 3500.0  # F_brake_max [N] (Hydraulic service brake capacity limit)


@dataclass
class PowertrainParameters:
    motor_rated_power: float = 5000.0  # P_rated [W] (Continuous rated motor power: 5.0 kW)
    motor_peak_power: float = 12000.0  # P_peak [W] (Short-duration peak motor power: 12.0 kW)
    motor_peak_torque: float = 75.0    # T_max [Nm] (Motor shaft peak torque)
    motor_max_rpm: float = 5500.0      # RPM_max [rev/min] (Cut-off motor rotational speed)
    gear_ratio: float = 4.2            # G [-] (Single-speed reduction gearbox ratio)
    drivetrain_efficiency: float = 0.96 # eta_trans [-] (Transmission/chain efficiency)
    motor_base_efficiency: float = 0.92 # eta_m [-] (Nominal electric motor efficiency)


@dataclass
class BatteryParameters:
    nominal_voltage: float = 96.0      # V_nom [V] (26S LiFePO4 / NMC battery pack architecture)
    capacity_ah: float = 50.0          # Q [Ah] (Nominal total pack charge capacity: 4.8 kWh)
    internal_resistance: float = 0.045 # R_int [Ohm] (Internal pack DC resistance)
    initial_soc: float = 90.0          # SOC_0 [%] (Initial state of charge at lap start)
    max_discharge_current: float = 140.0 # I_dis_max [A] (Peak continuous cell discharge limit)
    max_charge_current: float = 70.0   # I_chg_max [A] (Peak cell regenerative charge limit)
    regen_efficiency: float = 0.70     # eta_regen [-] (Regenerative braking energy recovery efficiency)
    max_regen_power: float = 7000.0    # P_regen_max [W] (Electrical regen absorption ceiling)


@dataclass
class SolarArrayParameters:
    array_area: float = 4.0            # A_pv [m^2] (Sun-facing photovoltaic panel area on upper shell)
    cell_efficiency: float = 0.22      # eta_pv [-] (High-efficiency monocrystalline silicon/gallium cells)
    mppt_efficiency: float = 0.97      # eta_mppt [-] (Maximum Power Point Tracking DC-DC converter efficiency)


@dataclass
class TrackParameters:
    name: str = "Kari Motor Speedway"
    location: str = "Coimbatore, Tamil Nadu, India"
    length_m: float = 2120.0           # Approximate circuit centreline distance
    turns_count: int = 14              # Official turn count
    track_width_m: float = 11.0        # Average asphalt width
    direction: str = "Anti-clockwise"
    is_approximate: bool = True        # Explicit label: mathematical reconstruction of circuit geometry


class HeliosConfig:
    """
    Centralized Vehicle and Simulation Configuration Container
    """
    def __init__(
        self,
        env: EnvironmentalParameters = None,
        aero: AerodynamicParameters = None,
        chassis: ChassisParameters = None,
        powertrain: PowertrainParameters = None,
        battery: BatteryParameters = None,
        solar: SolarArrayParameters = None,
        track: TrackParameters = None
    ):
        self.env = env or EnvironmentalParameters()
        self.aero = aero or AerodynamicParameters()
        self.chassis = chassis or ChassisParameters()
        self.powertrain = powertrain or PowertrainParameters()
        self.battery = battery or BatteryParameters()
        self.solar = solar or SolarArrayParameters()
        self.track = track or TrackParameters()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "env": asdict(self.env),
            "aero": asdict(self.aero),
            "chassis": asdict(self.chassis),
            "powertrain": asdict(self.powertrain),
            "battery": asdict(self.battery),
            "solar": asdict(self.solar),
            "track": asdict(self.track),
        }

    @classmethod
    def default(cls) -> "HeliosConfig":
        return cls()

