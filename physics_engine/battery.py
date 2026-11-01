"""
Battery & Energy Storage Physics Model
Simulates lithium battery chemistry with internal resistance equivalent circuit model,
open-circuit voltage state of charge non-linearity, and thermal/power limiters.
"""

from dataclasses import dataclass
import numpy as np
from config import BatteryParameters


@dataclass
class BatteryState:
    soc_pct: float               # State of Charge [%] (0.0 to 100.0)
    terminal_voltage: float      # Terminal voltage under load [V]
    open_circuit_voltage: float  # Unloaded pack voltage [V]
    current_a: float             # Pack current [A] (+ = discharge, - = charge/regen)
    power_w: float               # Pack electrical power [W] (+ = output, - = input)
    energy_consumed_j: float     # Cumulative gross discharged energy [Joules]
    energy_regenerated_j: float    # Cumulative regenerative energy harvested [Joules]
    net_energy_j: float          # Net energy consumed [Joules]
    net_energy_kwh: float        # Net energy consumed [kWh]


class BatteryPack:
    """
    Electrochemical equivalent circuit model of the traction battery pack.
    """
    def __init__(self, battery_params: BatteryParameters):
        self.p = battery_params
        self.soc = float(self.p.initial_soc)
        self.energy_consumed_j = 0.0
        self.energy_regenerated_j = 0.0

    def reset(self, initial_soc: float = None):
        """Resets battery state for a fresh simulation run."""
        self.soc = float(initial_soc if initial_soc is not None else self.p.initial_soc)
        self.energy_consumed_j = 0.0
        self.energy_regenerated_j = 0.0

    def compute_ocv(self, soc_pct: float) -> float:
        """
        Calculates open circuit voltage (OCV) as a realistic function of State of Charge.
        Captures the plateau characteristic of lithium cells with voltage drop at low SOC
        and steep rise near full charge.
        """
        s = np.clip(soc_pct / 100.0, 0.001, 1.0)
        # OCV approximation curve relative to nominal pack voltage
        # At 100% SOC: ~1.05 * V_nom
        # At 50% SOC:  ~1.00 * V_nom
        # At 10% SOC:  ~0.90 * V_nom
        ocv_ratio = 0.88 + 0.17 * s - 0.04 * np.exp(-12.0 * s) + 0.02 * (s ** 3)
        return float(self.p.nominal_voltage * ocv_ratio)

    def step(self, electrical_power_demand_w: float, dt: float) -> BatteryState:
        """
        Updates battery state over time step dt (seconds) given demanded electrical power (Watts).
        electrical_power_demand_w > 0: Motoring / Discharging
        electrical_power_demand_w < 0: Regenerative charging
        """
        if dt <= 0:
            ocv = self.compute_ocv(self.soc)
            return BatteryState(
                soc_pct=self.soc,
                terminal_voltage=ocv,
                open_circuit_voltage=ocv,
                current_a=0.0,
                power_w=0.0,
                energy_consumed_j=self.energy_consumed_j,
                energy_regenerated_j=self.energy_regenerated_j,
                net_energy_j=self.energy_consumed_j - self.energy_regenerated_j,
                net_energy_kwh=(self.energy_consumed_j - self.energy_regenerated_j) / 3.6e6
            )

        ocv = self.compute_ocv(self.soc)
        r = self.p.internal_resistance

        # Constrain regen power and charging limits if charging
        if electrical_power_demand_w < 0:
            # Regen charging
            max_regen_p = min(self.p.max_regen_power, ocv * self.p.max_charge_current)
            power_target = max(electrical_power_demand_w, -max_regen_p)
            # If battery is already at or above 99.5%, limit regen to avoid overcharge
            if self.soc >= 99.5:
                power_target = 0.0
        else:
            # Motoring discharge
            max_discharge_p = min(ocv * self.p.max_discharge_current, (ocv ** 2) / (4.0 * r))
            # If battery is critically depleted (< 5%), limit discharge
            if self.soc <= 5.0:
                max_discharge_p *= (self.soc / 5.0)
            power_target = min(electrical_power_demand_w, max_discharge_p)

        # Solve quadratic circuit equation: R * I^2 - OCV * I + P = 0
        discriminant = ocv ** 2 - 4.0 * r * power_target
        if discriminant < 0:
            # Theoretical max power limit reached
            current = ocv / (2.0 * r)
            terminal_voltage = ocv - current * r
            power_actual = terminal_voltage * current
        else:
            # Normal solution for current (discharge > 0, charge < 0)
            current = (ocv - np.sqrt(discriminant)) / (2.0 * r)
            terminal_voltage = ocv - current * r
            power_actual = terminal_voltage * current

        # Current limits enforcement
        current = float(np.clip(current, -self.p.max_charge_current, self.p.max_discharge_current))
        terminal_voltage = float(ocv - current * r)
        power_actual = float(terminal_voltage * current)

        # SOC Integration: dSOC = - (I * dt) / (Capacity in Coulombs) * 100%
        # Capacity in Coulombs = Capacity_Ah * 3600
        total_coulombs = self.p.capacity_ah * 3600.0
        dsoc = -(current * dt) / total_coulombs * 100.0
        self.soc = float(np.clip(self.soc + dsoc, 0.0, 100.0))

        # Energy tracking (Joules)
        if power_actual > 0:
            self.energy_consumed_j += power_actual * dt
        else:
            self.energy_regenerated_j += (-power_actual) * dt

        net_j = self.energy_consumed_j - self.energy_regenerated_j

        return BatteryState(
            soc_pct=self.soc,
            terminal_voltage=terminal_voltage,
            open_circuit_voltage=ocv,
            current_a=current,
            power_w=power_actual,
            energy_consumed_j=self.energy_consumed_j,
            energy_regenerated_j=self.energy_regenerated_j,
            net_energy_j=net_j,
            net_energy_kwh=net_j / 3.6e6
        )

