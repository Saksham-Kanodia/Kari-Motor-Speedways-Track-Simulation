"""
Interactive Plotly and Matplotlib Visualization Suite for HELIOS
Motorsport-grade dark telemetry styling, real-time vehicle cursor positioning,
and multi-channel engineering telemetry overlays.
"""

import os
from typing import Optional, Dict, Any
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


class HeliosPlotter:
    """
    Produces high-fidelity interactive telemetry plots and static figures.
    """
    DARK_THEME = {
        "bg_color": "#0e1117",
        "paper_color": "#161b22",
        "grid_color": "#30363d",
        "text_color": "#f0f6fc",
        "cyan": "#00e5ff",
        "gold": "#ffd600",
        "green": "#00e676",
        "red": "#ff1744",
        "purple": "#d500f9",
        "orange": "#ff9100"
    }

    @classmethod
    def apply_dark_layout(cls, fig: go.Figure, title: str = "", height: int = 380) -> go.Figure:
        fig.update_layout(
            title=dict(text=f"<b>{title}</b>", font=dict(color=cls.DARK_THEME["text_color"], size=14)),
            paper_bgcolor=cls.DARK_THEME["paper_color"],
            plot_bgcolor=cls.DARK_THEME["bg_color"],
            font=dict(family="Inter, Roboto, sans-serif", color=cls.DARK_THEME["text_color"], size=11),
            margin=dict(l=45, r=25, t=40, b=35),
            height=height,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1.0,
                bgcolor="rgba(22, 27, 34, 0.7)",
                font=dict(size=10)
            ),
            xaxis=dict(
                gridcolor=cls.DARK_THEME["grid_color"],
                zerolinecolor=cls.DARK_THEME["grid_color"],
                color=cls.DARK_THEME["text_color"]
            ),
            yaxis=dict(
                gridcolor=cls.DARK_THEME["grid_color"],
                zerolinecolor=cls.DARK_THEME["grid_color"],
                color=cls.DARK_THEME["text_color"]
            )
        )
        return fig

    @classmethod
    def create_track_map(
        cls,
        telemetry_df: pd.DataFrame,
        current_time_s: Optional[float] = None,
        color_channel: str = "speed_kmh"
    ) -> go.Figure:
        """
        Interactive top-down 2D representation of Kari Motor Speedway.
        Includes track centerline heatmapped by velocity/curvature/power,
        start/finish marker, and current vehicle position.
        """
        fig = go.Figure()

        # Track centerline colored by metric
        color_val = telemetry_df[color_channel] if color_channel in telemetry_df.columns else telemetry_df["speed_kmh"]
        c_title = {
            "speed_kmh": "Speed (km/h)",
            "motor_elec_power_kw": "Motor Power (kW)",
            "accel_y_g": "Lat Accel (g)",
            "sector": "Sector"
        }.get(color_channel, color_channel)

        # 1. Base asphalt circuit boundary outline
        fig.add_trace(go.Scatter(
            x=telemetry_df["x_m"],
            y=telemetry_df["y_m"],
            mode="lines",
            line=dict(color="#21262d", width=10),
            hoverinfo="skip",
            showlegend=False
        ))

        # 2. Telemetry metric heatmapped track points
        fig.add_trace(go.Scatter(
            x=telemetry_df["x_m"],
            y=telemetry_df["y_m"],
            mode="markers",
            marker=dict(
                size=5,
                color=color_val,
                colorscale="Viridis" if color_channel == "sector" else "Plasma",
                colorbar=dict(
                    title=dict(text=c_title, font=dict(color=cls.DARK_THEME["text_color"], size=10)),
                    tickfont=dict(color=cls.DARK_THEME["text_color"], size=9),
                    len=0.75,
                    thickness=12,
                    x=1.02
                )
            ),
            hoverinfo="text",
            text=[f"Dist: {d:.0f}m<br>Speed: {v:.1f} km/h<br>Sec: {s}"
                  for d, v, s in zip(telemetry_df["distance_m"], telemetry_df["speed_kmh"], telemetry_df["sector"])],
            name="Track Centerline"
        ))

        # Start / Finish Line marker
        fig.add_trace(go.Scatter(
            x=[telemetry_df["x_m"].iloc[0]],
            y=[telemetry_df["y_m"].iloc[0]],
            mode="markers+text",
            marker=dict(size=12, color=cls.DARK_THEME["gold"], symbol="diamond"),
            text=["START / FINISH"],
            textposition="bottom center",
            textfont=dict(color=cls.DARK_THEME["gold"], size=10),
            name="Start/Finish"
        ))

        # Current vehicle position marker
        if current_time_s is not None:
            times = telemetry_df["time_s"].values
            idx = int(np.clip(np.searchsorted(times, current_time_s), 0, len(telemetry_df) - 1))
            veh_x = telemetry_df["x_m"].iloc[idx]
            veh_y = telemetry_df["y_m"].iloc[idx]
            veh_speed = telemetry_df["speed_kmh"].iloc[idx]

            fig.add_trace(go.Scatter(
                x=[veh_x],
                y=[veh_y],
                mode="markers",
                marker=dict(
                    size=16,
                    color=cls.DARK_THEME["cyan"],
                    line=dict(color="#ffffff", width=2),
                    symbol="circle"
                ),
                hoverinfo="text",
                text=[f"HELIOS<br>{veh_speed:.1f} km/h"],
                name="Vehicle Position"
            ))

        cls.apply_dark_layout(fig, title="Kari Motor Speedway — Top-Down Track & Vehicle Tracking", height=450)
        fig.update_yaxes(scaleanchor="x", scaleratio=1)
        fig.update_xaxes(title="West - East Displacement (m)")
        fig.update_yaxes(title="South - North Displacement (m)")
        return fig

    @classmethod
    def create_speed_trace(cls, telemetry_df: pd.DataFrame, current_time_s: Optional[float] = None) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=telemetry_df["time_s"],
            y=telemetry_df["speed_kmh"],
            mode="lines",
            line=dict(color=cls.DARK_THEME["cyan"], width=2.5),
            name="Speed (km/h)"
        ))
        if current_time_s is not None:
            fig.add_vline(x=current_time_s, line_width=1.5, line_dash="dash", line_color=cls.DARK_THEME["gold"])

        cls.apply_dark_layout(fig, title="Vehicle Velocity vs Time", height=320)
        fig.update_xaxes(title="Elapsed Time (s)")
        fig.update_yaxes(title="Speed (km/h)")
        return fig

    @classmethod
    def create_powertrain_trace(cls, telemetry_df: pd.DataFrame, current_time_s: Optional[float] = None) -> go.Figure:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(
            x=telemetry_df["time_s"],
            y=telemetry_df["motor_rpm"],
            mode="lines",
            line=dict(color=cls.DARK_THEME["orange"], width=2),
            name="Motor RPM"
        ), secondary_y=False)

        fig.add_trace(go.Scatter(
            x=telemetry_df["time_s"],
            y=telemetry_df["motor_elec_power_kw"],
            mode="lines",
            line=dict(color=cls.DARK_THEME["green"], width=2),
            name="Electric Power (kW)"
        ), secondary_y=True)

        if current_time_s is not None:
            fig.add_vline(x=current_time_s, line_width=1.5, line_dash="dash", line_color=cls.DARK_THEME["gold"])

        cls.apply_dark_layout(fig, title="Powertrain Dynamics: Motor RPM & Electric Power", height=320)
        fig.update_xaxes(title="Elapsed Time (s)")
        fig.update_yaxes(title_text="Motor Speed (RPM)", secondary_y=False)
        fig.update_yaxes(title_text="Power Demand (kW)", secondary_y=True)
        return fig

    @classmethod
    def create_battery_trace(cls, telemetry_df: pd.DataFrame, current_time_s: Optional[float] = None) -> go.Figure:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(
            x=telemetry_df["time_s"],
            y=telemetry_df["battery_soc_pct"],
            mode="lines",
            line=dict(color=cls.DARK_THEME["cyan"], width=2.5),
            name="Battery SOC (%)"
        ), secondary_y=False)

        fig.add_trace(go.Scatter(
            x=telemetry_df["time_s"],
            y=telemetry_df["battery_current_a"],
            mode="lines",
            line=dict(color=cls.DARK_THEME["purple"], width=1.8),
            name="Pack Current (A)"
        ), secondary_y=True)

        if current_time_s is not None:
            fig.add_vline(x=current_time_s, line_width=1.5, line_dash="dash", line_color=cls.DARK_THEME["gold"])

        cls.apply_dark_layout(fig, title="Battery State of Charge & Current vs Time", height=320)
        fig.update_xaxes(title="Elapsed Time (s)")
        fig.update_yaxes(title_text="SOC (%)", secondary_y=False)
        fig.update_yaxes(title_text="Current (A) [+Disch, -Regen]", secondary_y=True)
        return fig

    @classmethod
    def create_dynamics_trace(cls, telemetry_df: pd.DataFrame, current_time_s: Optional[float] = None) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=telemetry_df["time_s"],
            y=telemetry_df["accel_x_g"],
            mode="lines",
            line=dict(color=cls.DARK_THEME["cyan"], width=2),
            name="Longitudinal Accel (g)"
        ))
        fig.add_trace(go.Scatter(
            x=telemetry_df["time_s"],
            y=telemetry_df["accel_y_g"],
            mode="lines",
            line=dict(color=cls.DARK_THEME["red"], width=1.8),
            name="Lateral Accel (g)"
        ))

        if current_time_s is not None:
            fig.add_vline(x=current_time_s, line_width=1.5, line_dash="dash", line_color=cls.DARK_THEME["gold"])

        cls.apply_dark_layout(fig, title="Chassis Accelerations (G-Forces) vs Time", height=320)
        fig.update_xaxes(title="Elapsed Time (s)")
        fig.update_yaxes(title="Acceleration (g)")
        return fig

    @classmethod
    def create_energy_trace(cls, telemetry_df: pd.DataFrame, current_time_s: Optional[float] = None) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=telemetry_df["distance_m"],
            y=telemetry_df["energy_consumed_kwh"],
            mode="lines",
            line=dict(color=cls.DARK_THEME["orange"], width=2),
            name="Gross Energy Consumed (kWh)"
        ))
        fig.add_trace(go.Scatter(
            x=telemetry_df["distance_m"],
            y=telemetry_df["energy_regenerated_kwh"],
            mode="lines",
            line=dict(color=cls.DARK_THEME["green"], width=2),
            name="Regenerative Energy (kWh)"
        ))
        fig.add_trace(go.Scatter(
            x=telemetry_df["distance_m"],
            y=telemetry_df["solar_energy_kwh"],
            mode="lines",
            line=dict(color=cls.DARK_THEME["gold"], width=2),
            name="Solar PV Harvest (kWh)"
        ))
        fig.add_trace(go.Scatter(
            x=telemetry_df["distance_m"],
            y=telemetry_df["net_energy_kwh"],
            mode="lines",
            line=dict(color=cls.DARK_THEME["cyan"], width=2.5, dash="dash"),
            name="Net Battery Draw (kWh)"
        ))

        cls.apply_dark_layout(fig, title="Cumulative Energy Balances vs Distance", height=320)
        fig.update_xaxes(title="Distance along Circuit (m)")
        fig.update_yaxes(title="Energy (kWh)")
        return fig

    @classmethod
    def create_regen_trace(cls, telemetry_df: pd.DataFrame, current_time_s: Optional[float] = None) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=telemetry_df["time_s"],
            y=telemetry_df["regen_power_kw"],
            mode="lines",
            line=dict(color=cls.DARK_THEME["green"], width=2.2),
            name="Regen Power (kW)"
        ))
        if current_time_s is not None:
            fig.add_vline(x=current_time_s, line_width=1.5, line_dash="dash", line_color=cls.DARK_THEME["gold"])

        cls.apply_dark_layout(fig, title="Regenerative Braking Electrical Power vs Time", height=300)
        fig.update_xaxes(title="Elapsed Time (s)")
        fig.update_yaxes(title="Regen Power (kW)")
        return fig

    @classmethod
    def create_gg_diagram(cls, telemetry_df: pd.DataFrame, current_time_s: Optional[float] = None) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=telemetry_df["accel_y_g"],
            y=telemetry_df["accel_x_g"],
            mode="markers",
            marker=dict(
                size=4,
                color=telemetry_df["speed_kmh"],
                colorscale="Plasma",
                colorbar=dict(title=dict(text="Speed (km/h)", font=dict(color=cls.DARK_THEME["text_color"], size=10)), len=0.8, thickness=10),
                opacity=0.7
            ),
            name="Operating G-G Points"
        ))

        # Friction circle boundary
        theta = np.linspace(0, 2*np.pi, 200)
        mu_g = 1.15 # baseline grip
        fig.add_trace(go.Scatter(
            x=mu_g * np.cos(theta),
            y=mu_g * np.sin(theta),
            mode="lines",
            line=dict(color=cls.DARK_THEME["red"], width=1.5, dash="dash"),
            name="Tire Grip Limit (1.15g)"
        ))

        if current_time_s is not None:
            times = telemetry_df["time_s"].values
            idx = int(np.clip(np.searchsorted(times, current_time_s), 0, len(telemetry_df) - 1))
            fig.add_trace(go.Scatter(
                x=[telemetry_df["accel_y_g"].iloc[idx]],
                y=[telemetry_df["accel_x_g"].iloc[idx]],
                mode="markers",
                marker=dict(size=12, color=cls.DARK_THEME["cyan"], symbol="circle"),
                name="Current G-G"
            ))

        cls.apply_dark_layout(fig, title="G-G Friction Circle Diagram (a_x vs a_y)", height=380)
        fig.update_xaxes(title="Lateral Acceleration (g)")
        fig.update_yaxes(title="Longitudinal Acceleration (g)")
        fig.update_yaxes(scaleanchor="x", scaleratio=1)
        return fig

    @classmethod
    def create_forces_trace(cls, telemetry_df: pd.DataFrame) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=telemetry_df["distance_m"], y=telemetry_df["f_drive_n"], name="Drive Force (N)", line=dict(color=cls.DARK_THEME["green"], width=1.8)))
        fig.add_trace(go.Scatter(x=telemetry_df["distance_m"], y=telemetry_df["f_drag_n"], name="Aero Drag (N)", line=dict(color=cls.DARK_THEME["orange"], width=1.8)))
        fig.add_trace(go.Scatter(x=telemetry_df["distance_m"], y=telemetry_df["f_rolling_n"], name="Rolling Res. (N)", line=dict(color=cls.DARK_THEME["purple"], width=1.5)))
        fig.add_trace(go.Scatter(x=telemetry_df["distance_m"], y=telemetry_df["f_brake_n"], name="Braking Force (N)", line=dict(color=cls.DARK_THEME["red"], width=1.8)))

        cls.apply_dark_layout(fig, title="Longitudinal Forces vs Track Distance", height=320)
        fig.update_xaxes(title="Track Distance (m)")
        fig.update_yaxes(title="Force (N)")
        return fig

    @classmethod
    def save_static_telemetry_figures(cls, telemetry_df: pd.DataFrame, output_dir: str = "results") -> Dict[str, str]:
        """
        Generates high-resolution publication-grade PNG plots using Matplotlib for documentation/reports.
        """
        os.makedirs(output_dir, exist_ok=True)
        paths = {}

        plt.style.use("dark_background")

        # 1. Speed Profile & Elevation/Forces
        fig, ax = plt.subplots(figsize=(10, 4.5), dpi=200)
        ax.plot(telemetry_df["distance_m"], telemetry_df["speed_kmh"], color="#00e5ff", lw=2, label="Vehicle Speed (km/h)")
        ax.set_title("HELIOS — Velocity Profile around Kari Motor Speedway", fontsize=12, fontweight="bold", pad=12)
        ax.set_xlabel("Track Distance (m)", fontsize=10)
        ax.set_ylabel("Speed (km/h)", fontsize=10)
        ax.grid(True, linestyle="--", alpha=0.3)
        ax.legend(loc="upper right")
        p1 = os.path.join(output_dir, "speed_profile.png")
        fig.tight_layout()
        fig.savefig(p1)
        plt.close(fig)
        paths["speed_profile"] = p1

        # 2. Powertrain & Energy Summary
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, dpi=200)
        ax1.plot(telemetry_df["time_s"], telemetry_df["motor_elec_power_kw"], color="#00e676", lw=1.8, label="Motor Electrical Power (kW)")
        ax1.plot(telemetry_df["time_s"], telemetry_df["regen_power_kw"], color="#ffd600", lw=1.8, label="Regen Power (kW)")
        ax1.set_ylabel("Power (kW)", fontsize=9)
        ax1.grid(True, linestyle="--", alpha=0.3)
        ax1.legend(loc="upper right", fontsize=8)

        ax2.plot(telemetry_df["time_s"], telemetry_df["battery_soc_pct"], color="#00e5ff", lw=2, label="Battery SOC (%)")
        ax2.set_xlabel("Time (s)", fontsize=10)
        ax2.set_ylabel("SOC (%)", fontsize=9)
        ax2.grid(True, linestyle="--", alpha=0.3)
        ax2.legend(loc="lower right", fontsize=8)

        p2 = os.path.join(output_dir, "powertrain_telemetry.png")
        fig.tight_layout()
        fig.savefig(p2)
        plt.close(fig)
        paths["powertrain_telemetry"] = p2

        # 3. G-G Friction Circle
        fig, ax = plt.subplots(figsize=(6, 6), dpi=200)
        scatter = ax.scatter(telemetry_df["accel_y_g"], telemetry_df["accel_x_g"], c=telemetry_df["speed_kmh"], cmap="plasma", s=6, alpha=0.8)
        theta = np.linspace(0, 2*np.pi, 200)
        ax.plot(1.15 * np.cos(theta), 1.15 * np.sin(theta), "r--", lw=1.5, label="Tyre Limit (1.15g)")
        ax.set_title("G-G Acceleration Diagram", fontsize=11, fontweight="bold")
        ax.set_xlabel("Lateral Acceleration (g)", fontsize=10)
        ax.set_ylabel("Longitudinal Acceleration (g)", fontsize=10)
        ax.set_aspect("equal", "box")
        ax.grid(True, linestyle="--", alpha=0.3)
        plt.colorbar(scatter, ax=ax, label="Speed (km/h)", shrink=0.8)
        ax.legend(loc="upper right", fontsize=8)
        p3 = os.path.join(output_dir, "friction_circle_gg.png")
        fig.tight_layout()
        fig.savefig(p3)
        plt.close(fig)
        paths["friction_circle_gg"] = p3

        return paths
