"""
Unit tests for Vehicle Physics, Motor, and Lateral Dynamics models.
"""

import unittest
import numpy as np
from config import HeliosConfig
from physics_engine.vehicle import VehiclePhysics
from physics_engine.motor import ElectricMotor
from physics_engine.dynamics import LateralDynamics


class TestPhysics(unittest.TestCase):
    def setUp(self):
        self.cfg = HeliosConfig.default()
        self.vehicle = VehiclePhysics(self.cfg)
        self.motor = self.vehicle.motor
        self.dynamics = self.vehicle.dynamics

    def test_drag_increases_with_velocity_squared(self):
        """Test that aerodynamic drag scales strictly with v^2."""
        v1 = 10.0 # m/s
        v2 = 20.0 # m/s (2x speed)
        f_drag1 = self.vehicle.compute_aerodynamic_drag(v1)
        f_drag2 = self.vehicle.compute_aerodynamic_drag(v2)
        ratio = f_drag2 / f_drag1
        # Ratio should be approximately (20/10)^2 = 4.0
        self.assertAlmostEqual(ratio, 4.0, places=4)

    def test_rolling_resistance_opposes_motion(self):
        """Test that rolling resistance is positive when moving and zero when stationary."""
        f_rr_zero = self.vehicle.compute_rolling_resistance(0.0)
        f_rr_moving = self.vehicle.compute_rolling_resistance(15.0)
        self.assertEqual(f_rr_zero, 0.0)
        expected_f_rr = self.cfg.chassis.rolling_resistance_coeff * self.cfg.chassis.vehicle_mass * self.cfg.env.gravity
        self.assertAlmostEqual(f_rr_moving, expected_f_rr, places=3)

    def test_acceleration_positive_when_net_force_positive(self):
        """Test that vehicle acceleration is positive when driving force exceeds resistive forces."""
        # Low speed with max throttle: driving force should dominate
        res = self.vehicle.step(speed_mps=5.0, demanded_accel_mps2=1.5, dt=0.1)
        self.assertGreater(res["f_net"], 0.0)
        self.assertGreater(res["accel_x"], 0.0)
        self.assertGreater(res["f_drive"], res["f_drag"] + res["f_rolling"])

    def test_motor_torque_and_power_limits(self):
        """Test that motor limits peak torque and peak power."""
        # Low RPM (below base speed): Torque <= peak_torque
        low_rpm = 500.0
        torque_low = self.motor.get_max_motor_torque(low_rpm)
        self.assertLessEqual(torque_low, self.cfg.powertrain.motor_peak_torque + 1e-4)

        # High RPM: Power = Torque * omega <= peak_power
        high_rpm = 4000.0
        omega_high = high_rpm * (2.0 * np.pi) / 60.0
        torque_high = self.motor.get_max_motor_torque(high_rpm)
        mech_power = torque_high * omega_high
        self.assertLessEqual(mech_power, self.cfg.powertrain.motor_peak_power + 1e-3)

        # Over-rev limit: At or above max RPM, torque must be zero
        over_rpm = self.cfg.powertrain.motor_max_rpm + 10.0
        torque_over = self.motor.get_max_motor_torque(over_rpm)
        self.assertEqual(torque_over, 0.0)

    def test_cornering_speed_decreases_as_curvature_increases(self):
        """Test that maximum cornering speed decreases for sharper corners (larger curvature)."""
        k_gentle = 1.0 / 120.0  # R = 120m gentle bend
        k_sharp = 1.0 / 25.0    # R = 25m hairpin
        v_gentle = self.dynamics.compute_max_cornering_speed(k_gentle)
        v_sharp = self.dynamics.compute_max_cornering_speed(k_sharp)
        self.assertGreater(v_gentle, v_sharp)
        # Check physical formula: v = sqrt(mu * g / k)
        expected_v_sharp = np.sqrt(self.cfg.chassis.friction_coefficient * self.cfg.env.gravity * 0.98 / k_sharp)
        self.assertAlmostEqual(v_sharp, expected_v_sharp, places=3)


if __name__ == "__main__":
    unittest.main()

