"""
Unit and Integration Tests for Track Modeling and Lap Simulation.
"""

import unittest
import numpy as np
from config import HeliosConfig
from simulation.track import KariTrack
from simulation.lap_simulator import LapSimulator
from simulation.telemetry import TelemetryManager


class TestSimulation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.track = KariTrack(resolution_m=4.0) # slightly coarser for faster test execution
        cls.cfg = HeliosConfig.default()
        cls.simulator = LapSimulator(config=cls.cfg, track=cls.track)
        cls.telemetry_df, cls.summary = cls.simulator.run_lap()
        cls.telemetry_mgr = TelemetryManager(cls.telemetry_df, cls.summary)

    def test_track_properties(self):
        """Test track model properties and distance."""
        self.assertGreater(self.track.total_length_m, 2000.0)
        self.assertLess(self.track.total_length_m, 2500.0)
        track_df = self.track.get_track_data()
        self.assertIn("curvature_rad_m", track_df.columns)
        self.assertIn("sector", track_df.columns)

    def test_lap_simulation_completion(self):
        """Verify that simulation completes an entire lap from start to finish."""
        self.assertGreater(len(self.telemetry_df), 100)
        self.assertAlmostEqual(self.telemetry_df["distance_m"].iloc[0], 0.0, delta=1.0)
        self.assertAlmostEqual(self.telemetry_df["distance_m"].iloc[-1], self.track.total_length_m, delta=1.0)
        self.assertGreater(self.summary["lap_time_s"], 40.0)
        self.assertLess(self.summary["lap_time_s"], 180.0)

    def test_speed_within_physical_limits(self):
        """Verify speeds are non-negative and do not exceed motor and aerodynamic limits."""
        speeds = self.telemetry_df["speed_kmh"].values
        self.assertTrue(np.all(speeds > 0.0))
        # Solar EV peak speed should be physically credible (~80 to 140 km/h)
        self.assertLess(self.summary["max_speed_kmh"], 150.0)
        self.assertGreater(self.summary["min_speed_kmh"], 20.0)

    def test_telemetry_snapshot_interpolation(self):
        """Verify telemetry snapshot interpolates valid physical parameters."""
        halfway_time = self.summary["lap_time_s"] * 0.5
        snap = self.telemetry_mgr.get_snapshot_at_time(halfway_time)
        self.assertIn("speed_kmh", snap)
        self.assertIn("battery_soc_pct", snap)
        self.assertIn("motor_rpm", snap)
        self.assertIn("net_energy_kwh", snap)
        self.assertGreater(snap["speed_kmh"], 0.0)
        self.assertGreaterEqual(snap["battery_soc_pct"], 0.0)
        self.assertLessEqual(snap["battery_soc_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()

