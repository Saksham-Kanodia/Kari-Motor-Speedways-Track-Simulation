"""
Telemetry Manager & Telemetry Data Processing
Handles real-time interpolation for animated playback, data persistence,
and performance reporting.
"""

import os
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd


class TelemetryManager:
    """
    Manages telemetry dataframe interpolation, playback indexing, and data export.
    """
    def __init__(self, telemetry_df: Optional[pd.DataFrame] = None, summary: Optional[Dict[str, Any]] = None):
        self.df = telemetry_df
        self.summary = summary or {}

    def set_data(self, telemetry_df: pd.DataFrame, summary: Dict[str, Any]):
        self.df = telemetry_df
        self.summary = summary

    def get_snapshot_at_time(self, time_s: float) -> Dict[str, Any]:
        """
        Interpolates all telemetry parameters at continuous time t for smooth dashboard animation.
        """
        if self.df is None or len(self.df) == 0:
            return {}

        max_t = self.df["time_s"].iloc[-1]
        clamped_t = float(np.clip(time_s, 0.0, max_t))

        # Linear interpolation across columns
        times = self.df["time_s"].values
        idx = np.searchsorted(times, clamped_t)
        if idx == 0:
            row = self.df.iloc[0].to_dict()
        elif idx >= len(self.df):
            row = self.df.iloc[-1].to_dict()
        else:
            t0, t1 = times[idx - 1], times[idx]
            alpha = (clamped_t - t0) / max(t1 - t0, 1e-6)
            row0 = self.df.iloc[idx - 1]
            row1 = self.df.iloc[idx]
            row = {}
            for col in self.df.columns:
                if np.issubdtype(self.df[col].dtype, np.number):
                    row[col] = float(row0[col] + alpha * (row1[col] - row0[col]))
                else:
                    row[col] = row0[col]

        row["lap_progress_pct"] = (row["distance_m"] / self.df["distance_m"].iloc[-1]) * 100.0
        return row

    def export_csv(self, file_path: str = "results/sample_lap_telemetry.csv") -> str:
        """Exports the full telemetry dataframe to CSV."""
        if self.df is None:
            raise ValueError("No telemetry data to export.")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        self.df.to_csv(file_path, index=False)
        return file_path

