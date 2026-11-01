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
    Track Length: ~2,120 meters | Turns: 14 | Direction: Clockwise
    """
    def __init__(self, resolution_m: float = 2.0, data_dir: str = "data"):
        self.resolution_m = resolution_m
        self.data_dir = data_dir
        self.track_df = None
        self.turns_meta = []
        self._build_or_load_track()

    def _get_kari_waypoints(self) -> np.ndarray:
        """
        Centreline reconstruction traced from the supplied Kari Motor Speedway map.
        The map depicts the older ~2.1 km layout. Coordinates are schematic pixels,
        converted to a north-up Cartesian plane before metric calibration.
        Direction: clockwise from the main-straight start/finish point.
        """
        image_waypoints = np.array([
            [152.0, 52.0],
            [190.0, 49.0],
            [230.0, 47.0],
            [252.0, 46.0],
            [263.0, 49.0],
            [268.0, 57.0],
            [268.0, 70.0],
            [264.0, 83.0],
            [266.0, 90.0],
            [273.0, 93.0],
            [280.0, 90.0],
            [283.0, 83.0],
            [280.0, 68.0],
            [275.0, 52.0],
            [269.0, 37.0],
            [263.0, 22.0],
            [258.0, 15.0],
            [252.0, 12.0],
            [246.0, 13.0],
            [241.0, 18.0],
            [241.0, 25.0],
            [232.0, 27.0],
            [216.0, 27.0],
            [201.0, 25.0],
            [185.0, 25.0],
            [174.0, 27.0],
            [168.0, 31.0],
            [166.0, 39.0],
            [167.0, 48.0],
            [170.0, 51.0],
            [158.0, 52.0],
            [152.0, 51.0],
            [147.0, 48.0],
            [144.0, 43.0],
            [146.0, 37.0],
            [152.0, 33.0],
            [158.0, 30.0],
            [160.0, 26.0],
            [154.0, 24.0],
            [144.0, 25.0],
            [135.0, 29.0],
            [132.0, 36.0],
            [132.0, 45.0],
            [130.0, 51.0],
            [119.0, 52.0],
            [106.0, 53.0],
            [95.0, 53.0],
            [91.0, 49.0],
            [88.0, 43.0],
            [83.0, 40.0],
            [78.0, 41.0],
            [73.0, 43.0],
            [58.0, 45.0],
            [43.0, 47.0],
            [31.0, 49.0],
            [27.0, 46.0],
            [24.0, 42.0],
            [19.0, 40.0],
            [15.0, 43.0],
            [13.0, 50.0],
            [14.0, 57.0],
            [18.0, 60.0],
            [30.0, 60.0],
            [46.0, 59.0],
            [56.0, 58.0],
            [59.0, 61.0],
            [61.0, 65.0],
            [70.0, 65.0],
            [82.0, 65.0],
            [89.0, 62.0],
            [94.0, 57.0],
            [105.0, 56.0],
            [120.0, 54.0],
            [137.0, 53.0],
        ], dtype=float)

        # Light cyclic smoothing removes raster/waypoint noise without erasing chicanes.
        for _ in range(2):
            image_waypoints = np.array([
                0.1 * image_waypoints[(i - 2) % len(image_waypoints)]
                + 0.2 * image_waypoints[(i - 1) % len(image_waypoints)]
                + 0.4 * image_waypoints[i]
                + 0.2 * image_waypoints[(i + 1) % len(image_waypoints)]
                + 0.1 * image_waypoints[(i + 2) % len(image_waypoints)]
                for i in range(len(image_waypoints))
            ])

        return np.column_stack((image_waypoints[:, 0], -image_waypoints[:, 1]))

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
        tck_raw, _ = splprep([raw_points[:, 0], raw_points[:, 1]], s=8.0, per=True, k=3)
        u_probe = np.linspace(0.0, 1.0, 1000)
        x_probe, y_probe = splev(u_probe, tck_raw)
        raw_len = np.sum(np.sqrt(np.diff(x_probe)**2 + np.diff(y_probe)**2))
        scale = target_circuit_length / max(raw_len, 100.0)

        scaled_points = raw_points * scale

        # Fit periodic parametric spline (per=True for closed circuit)
        tck, u = splprep([scaled_points[:, 0], scaled_points[:, 1]], s=30.0, per=True, k=3)

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
