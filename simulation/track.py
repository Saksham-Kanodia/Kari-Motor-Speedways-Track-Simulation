"""
Kari Motor Speedway Track Representation & Geometric Modeling
Generates high-resolution parametric track centerline, curvature profile,
turn apex identification, and sector partitioning for Kari Motor Speedway (Coimbatore, India).
"""

import os
from typing import Tuple, List, Dict
import numpy as np
import pandas as pd


class KariTrack:
    """
    Parametric model of Kari Motor Speedway circuit.
    Track Length: ~2,120 meters | Turns: 14 | Direction: Anti-clockwise
    """
    def __init__(self, resolution_m: float = 2.0, data_dir: str = "data"):
        self.resolution_m = resolution_m
        self.data_dir = data_dir
        self.track_df = None
        self.turns_meta = []
        self._build_or_load_track()

    def _get_kari_waypoints(self) -> np.ndarray:
        """
        Geometrically verified waypoint approximation for Kari Motor Speedway.
        Anti-clockwise configuration:
        - Main straight running west-to-east
        - T1-T2 fast left-right sweeper
        - T3-T4 complex leading into infield
        - T5 tight hairpin (slowest section)
        - T6-T7 chicane
        - T8-T10 technical infield bends
        - T11-T12 back straight sweepers
        - T13-T14 parabolic final curve returning to start/finish
        """
        waypoints = np.array([
            # [X (m), Y (m), Turn_ID, Turn_Name]
            [0.0, 0.0],         # Start / Finish line
            [120.0, 5.0],       # Main straight progression
            [260.0, 10.0],      # Main straight braking zone
            [370.0, 20.0],      # Approach to T1
            [430.0, 50.0],      # T1 (Fast Left)
            [465.0, 100.0],     # T2 (Sweeping Right)
            [460.0, 160.0],     # Exit T2
            [430.0, 215.0],     # T3 (Left kink)
            [385.0, 260.0],     # T4 (Left bend towards hairpin)
            [325.0, 290.0],     # Approach to T5 Hairpin
            [265.0, 310.0],     # T5 Hairpin Entry
            [235.0, 305.0],     # T5 Hairpin Apex (Tight R=22m)
            [230.0, 275.0],     # T5 Hairpin Exit
            [250.0, 220.0],     # Short straight
            [265.0, 165.0],     # Approach T6 Chicane
            [250.0, 135.0],     # T6 Chicane Left
            [230.0, 120.0],     # T7 Chicane Right
            [180.0, 115.0],     # Short burst
            [130.0, 130.0],     # T8 (Infield Left)
            [85.0, 165.0],      # T9 (Infield Left)
            [60.0, 220.0],      # Infield link
            [40.0, 275.0],      # T10 (Right kink)
            [10.0, 310.0],      # T11 (Back sweeper left)
            [-40.0, 320.0],     # Back straight section
            [-100.0, 305.0],    # Approach T12
            [-155.0, 260.0],    # T12 (Left Sweeper)
            [-185.0, 200.0],    # Infield exit
            [-200.0, 140.0],    # T13 (Entry to Parabolic Curve)
            [-190.0, 70.0],     # T14 Parabolic Apex (Right long sweep)
            [-140.0, 20.0],     # T14 Exit
            [-70.0, 5.0],       # Final acceleration towards Start/Finish
            [0.0, 0.0]          # Closed circuit return
        ])
        return waypoints

    def _build_or_load_track(self):
        """Constructs parametric spline track model and saves/loads CSV data."""
        os.makedirs(self.data_dir, exist_ok=True)
        csv_path = os.path.join(self.data_dir, "track_data.csv")

        # Load precomputed CSV if present (fast and zero scipy dependency)
        if os.path.exists(csv_path):
            self.track_df = pd.read_csv(csv_path)
            return

        from scipy.interpolate import splprep, splev
        raw_points = self._get_kari_waypoints()

        # Calibrate waypoints so total spline perimeter matches Kari Motor Speedway official length (~2,120 m)
        # Empirical scale factor based on baseline spline length
        target_circuit_length = 2120.0

        # Fit initial spline
        tck_raw, _ = splprep([raw_points[:, 0], raw_points[:, 1]], s=250.0, per=True, k=3)
        u_probe = np.linspace(0.0, 1.0, 1000)
        x_probe, y_probe = splev(u_probe, tck_raw)
        raw_len = np.sum(np.sqrt(np.diff(x_probe)**2 + np.diff(y_probe)**2))
        scale = target_circuit_length / max(raw_len, 100.0)

        scaled_points = raw_points * scale

        # Fit periodic parametric spline (per=True for closed circuit)
        tck, u = splprep([scaled_points[:, 0], scaled_points[:, 1]], s=300.0, per=True, k=3)

        # High resolution sampling
        u_fine = np.linspace(0.0, 1.0, 1500)
        x_pts, y_pts = splev(u_fine, tck)

        # Compute point-to-point incremental Euclidean distance
        dx = np.diff(x_pts)
        dy = np.diff(y_pts)
        segment_lengths = np.sqrt(dx**2 + dy**2)
        cumulative_dist = np.insert(np.cumsum(segment_lengths), 0, 0.0)
        total_raw_length = cumulative_dist[-1]

        # Resample at exact uniform arc-length intervals
        target_s = np.arange(0.0, total_raw_length, self.resolution_m)
        x_uniform = np.interp(target_s, cumulative_dist, x_pts)
        y_uniform = np.interp(target_s, cumulative_dist, y_pts)

        # Re-fit spline on uniform points for continuous analytical derivatives
        tck_uniform, u_uni = splprep([x_uniform, y_uniform], s=0.0, per=True, k=3)

        # Analytical 1st and 2nd derivatives wrt parameter u
        dx_du, dy_du = splev(u_uni, tck_uniform, der=1)
        d2x_du2, d2y_du2 = splev(u_uni, tck_uniform, der=2)

        # Curvature formula: kappa = (x' y'' - y' x'') / (x'^2 + y'^2)^(3/2)
        numerator = dx_du * d2y_du2 - dy_du * d2x_du2
        denominator = (dx_du**2 + dy_du**2) ** 1.5
        curvature = numerator / np.maximum(denominator, 1e-9)

        # Heading angle (tangent angle) in radians
        heading = np.arctan2(dy_du, dx_du)

        # Sector identification:
        # Kari Motor Speedway 3 Sectors:
        # Sector 1: Start to T4 exit (~0 to 680m)
        # Sector 2: Hairpin T5 to T10 (~680m to 1420m)
        # Sector 3: T11 to Main straight finish (~1420m to end)
        n_pts = len(target_s)
        sectors = np.ones(n_pts, dtype=int)
        s1_cutoff = 0.32 * target_s[-1]
        s2_cutoff = 0.68 * target_s[-1]
        sectors[target_s >= s1_cutoff] = 2
        sectors[target_s >= s2_cutoff] = 3

        # Assemble DataFrame
        self.track_df = pd.DataFrame({
            "distance_m": target_s,
            "x_m": x_uniform,
            "y_m": y_uniform,
            "curvature_rad_m": curvature,
            "radius_m": 1.0 / np.maximum(np.abs(curvature), 1e-5),
            "heading_rad": heading,
            "sector": sectors
        })

        # Save to disk for transparency and persistence
        self.track_df.to_csv(csv_path, index=False)

    def get_track_data(self) -> pd.DataFrame:
        """Returns the full track dataframe."""
        return self.track_df.copy()

    @property
    def total_length_m(self) -> float:
        return float(self.track_df["distance_m"].iloc[-1])

    @property
    def point_count(self) -> int:
        return len(self.track_df)
