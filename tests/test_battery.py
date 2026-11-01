"""
Unit tests for BatteryPack and electrochemical physics model.
"""

import unittest
from config import HeliosConfig, BatteryParameters
from physics_engine.battery import BatteryPack


class TestBattery(unittest.TestCase):
    def setUp(self):
        self.params = BatteryParameters(
            nominal_voltage=96.0,
            capacity_ah=50.0,
            internal_resistance=0.045,
            initial_soc=90.0,
            max_discharge_current=140.0,
            max_charge_current=70.0,
            regen_efficiency=0.70,
            max_regen_power=7000.0
        )
        self.battery = BatteryPack(self.params)

    def test_soc_decreases_on_discharge(self):
        """Test that battery SOC decreases during net discharge."""
        init_soc = self.battery.soc
        state = self.battery.step(electrical_power_demand_w=5000.0, dt=10.0) # 5kW discharge for 10s
        self.assertLess(state.soc_pct, init_soc)
        self.assertGreater(state.current_a, 0.0)
        self.assertGreater(state.power_w, 0.0)
        self.assertGreater(state.energy_consumed_j, 0.0)

    def test_soc_increases_on_regen_charge(self):
        """Test that battery SOC increases during valid regenerative charging."""
        self.battery.reset(initial_soc=80.0)
        init_soc = self.battery.soc
        state = self.battery.step(electrical_power_demand_w=-4000.0, dt=10.0) # -4kW regen for 10s
        self.assertGreater(state.soc_pct, init_soc)
        self.assertLess(state.current_a, 0.0)
        self.assertLess(state.power_w, 0.0)
        self.assertGreater(state.energy_regenerated_j, 0.0)

    def test_soc_never_exceeds_100_or_below_0(self):
        """Test that SOC is constrained strictly between 0% and 100%."""
        # Overcharge test
        self.battery.reset(initial_soc=99.9)
        for _ in range(50):
            state = self.battery.step(electrical_power_demand_w=-8000.0, dt=60.0)
        self.assertLessEqual(state.soc_pct, 100.0)

        # Over-discharge test
        self.battery.reset(initial_soc=0.5)
        for _ in range(50):
            state = self.battery.step(electrical_power_demand_w=10000.0, dt=60.0)
        self.assertGreaterEqual(state.soc_pct, 0.0)

    def test_terminal_voltage_sag_under_load(self):
        """Test that terminal voltage is less than OCV under discharge load (V = OCV - I*R)."""
        self.battery.reset(initial_soc=85.0)
        state = self.battery.step(electrical_power_demand_w=6000.0, dt=1.0)
        self.assertLess(state.terminal_voltage, state.open_circuit_voltage)


if __name__ == "__main__":
    unittest.main()

