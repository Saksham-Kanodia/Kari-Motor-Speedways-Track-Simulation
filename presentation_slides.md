# HELIOS: Physics-Based Solar EV Digital Twin & Kari Motor Speedway Simulator
## Technical Engineering Presentation

---

### Slide 1: HELIOS — Physics-Based Solar EV Digital Twin
**Subtitle:** First-Principles Telemetry & Lap Simulation around Kari Motor Speedway  
**Author:** Senior Automotive Simulation & Dynamics Engineer  
**Date:** November 2026  
**System:** Python 3.14 | Streamlit 1.62 | NumPy 2.4 | Plotly 7.1  

- **Project Core:** High-fidelity vehicle digital twin combining longitudinal vehicle dynamics, electrical powertrain modeling, lithium electrochemical battery modeling, and photovoltaic energy harvesting.
- **Circuit Venue:** Kari Motor Speedway (Coimbatore, India) — 2,120 m, 14 turns, anti-clockwise.
- **Engineering Philosophy:** Rigorous physical models over synthetic numbers; real forward-backward lap velocity solver; responsive motorsport cockpit telemetry dashboard.

---

### Slide 2: Problem Statement and Objectives
**Challenge:** Design, simulate, and analyze the performance of a high-efficiency Solar Electric Vehicle navigating a technical racing circuit under physical power, grip, and energy constraints.

**Primary Engineering Objectives:**
1. **Mathematical Physics Modeling:** Model vehicle resistances ($F_{\text{drag}}, F_{\text{rolling}}$), motor torque-power envelopes, battery SOC/voltage sag, and regenerative braking.
2. **Track Representation:** Build an analytical 2D model of Kari Motor Speedway with continuous curvature and sector segmentation.
3. **Quasi-Steady State Lap Simulation:** Develop a two-pass forward acceleration and backward braking solver to evaluate maximum achievable lap performance.
4. **Real-Time Interactive Telemetry Dashboard:** Provide an automotive-grade Streamlit telemetry interface with live vehicle tracking, HUD metric cards, and multi-channel telemetry inspection.
5. **Data Export & Reproducibility:** Deliver validated test suites, downloadable telemetry CSV datasets, and automated summary reports.

---

### Slide 3: Vehicle Specifications and Configuration
*Parameters reflect provisional engineering specifications for a single-seater Solar Racing EV prototype.*

| Subsystem | Parameter | Value | Engineering Assumption / Basis |
|---|---|---|---|
| **Chassis** | Total Mass ($m$) | 320.0 kg | Vehicle curb weight (245 kg) + 75 kg driver |
| **Aerodynamics** | Drag Coeff ($C_d$) | 0.20 | Streamlined solar canopy bodywork |
| **Aerodynamics** | Frontal Area ($A$) | 1.15 m² | Low-frontal single-seater profile |
| **Tyres** | Rolling Res ($C_{rr}$) | 0.007 | Low-resistance solar racing compound |
| **Tyres** | Grip Coeff ($\mu$) | 1.15 | Warm dry asphalt grip limit at Kari Speedway |
| **Powertrain** | Motor Peak Power | 12.0 kW | Permanent Magnet Synchronous Motor (PMSM) |
| **Powertrain** | Motor Peak Torque | 75.0 Nm | Low-speed acceleration limit |
| **Powertrain** | Max Motor RPM | 5,500 RPM | Rotational redline ($G=4.2$, $r_w=0.28\text{ m}$) |
| **Battery Pack** | Architecture | 96 V / 50 Ah | 26S Lithium Pack (~4.8 kWh total capacity) |
| **Solar Array** | PV Area / Eff. | 4.0 m² / 22% | Monocrystalline Si cells with MPPT converter |

---

### Slide 4: Mathematical and Physics Modelling
*All vehicle telemetry originates from first-principles governing equations.*

1. **Longitudinal Equation of Motion:**
   $$m \cdot a_x = F_{\text{drive}} - F_{\text{drag}} - F_{\text{rolling}} - F_{\text{braking}}$$
   - Aerodynamic Drag: $F_{\text{drag}} = 0.5 \cdot \rho \cdot C_d \cdot A \cdot v^2$
   - Rolling Resistance: $F_{\text{rolling}} = C_{rr} \cdot m \cdot g$
2. **Motor Dual-Regime Model:**
   - Constant Torque: $T = 75.0\text{ Nm}$ for $\omega \le \omega_{\text{base}}$ ($\omega_{\text{base}} = 160\text{ rad/s} \approx 1528\text{ RPM}$)
   - Constant Power: $T = P_{\text{peak}} / \omega$ for $\omega_{\text{base}} < \omega \le \omega_{\text{max}}$
3. **Battery Electrochemical Equivalent Circuit:**
   - Non-linear OCV curve: $V_{\text{ocv}}(SOC)$ with internal resistance $R_{\text{int}} = 0.045\,\Omega$
   - Terminal voltage: $V_{\text{term}} = V_{\text{ocv}} - I \cdot R_{\text{int}}$
   - Net Power Demand: $P_{\text{net}} = P_{\text{motor}} - P_{\text{solar}} - P_{\text{regen}}$
4. **Friction Circle Adhesion Constraint (Kamm's Circle):**
   $$\left(\frac{a_x}{\mu g}\right)^2 + \left(\frac{a_y}{\mu g}\right)^2 \le 1.0 \implies a_{x,\text{max}} = \mu g \sqrt{1 - \left(\frac{a_y}{\mu g}\right)^2}$$

---

### Slide 5: Kari Motor Speedway Track Modelling
*Coimbatore, Tamil Nadu, India — 2,120 m Length | 14 Turns | Anti-Clockwise*

- **Centerline Spline Model:** Parametric cubic spline ($X(s), Y(s)$) sampled at uniform $\Delta s = 2.0\text{ m}$ (1,060 discrete points).
- **Curvature Calculation:** $\kappa(s) = \frac{x' y'' - y' x''}{(x'^2 + y'^2)^{3/2}}$
- **Cornering Velocity Limit:** $v_{\text{corner}}(s) = \sqrt{\frac{\mu \cdot g \cdot 0.98}{\max(|\kappa(s)|, 10^{-6})}}$
- **Sector Decomposition:**
  - **Sector 1 (0 to 678 m):** 500m Main Straight, Turn 1 & 2 Fast Sweeper, Turn 3 entry.
  - **Sector 2 (678 to 1441 m):** Turn 4, Turn 5 Hairpin ($R \approx 22\text{ m}$, slowest point on circuit), Turn 6-7 chicane, Turn 8-10 infield.
  - **Sector 3 (1441 to 2120 m):** Turn 11-12 sweepers, Turn 13-14 Parabolic final curve.
- **Model Classification:** Labelled as a provisional validated mathematical model, fully replaceable with surveyed DGPS coordinates.

---

### Slide 6: Lap Simulation and Vehicle Performance
*Numerical Results from Two-Pass Velocity Profile Algorithm.*

```text
Forward Pass:  Accelerate out of corners bounded by motor power & grip limit
Backward Pass: Brake into corners backwards bounded by braking force & grip
Result:        Continuous, cyclic velocity profile across start/finish line
```

- **Lap Time:** **73.93 seconds** (~1 min 13.93 s)
- **Sector Splits:** S1 = **23.81 s**, S2 = **28.95 s**, S3 = **21.16 s**
- **Top Speed:** **129.2 km/h** (achieved at the end of the 500m main straight)
- **Minimum Corner Speed:** **51.4 km/h** (at Turn 5 Hairpin apex)
- **Average Lap Velocity:** **103.1 km/h**
- **Peak Dynamic Accelerations:**
  - Peak Forward Acceleration: $+2.31\text{ m/s}^2$ ($+0.24\text{ g}$)
  - Peak Braking Deceleration: $-11.47\text{ m/s}^2$ ($-1.17\text{ g}$)
  - Peak Cornering Lateral Acceleration: $11.05\text{ m/s}^2$ ($1.13\text{ g}$)

---

### Slide 7: Real-Time Telemetry Dashboard
*Automotive Engineering Cockpit built with Streamlit & Plotly.*

- **Motorsport Dark Theme:** High-contrast dark grey aesthetic (`#0d1117`), electric cyan, racing green, and solar gold accents.
- **Live Digital HUD Gauges:**
  - Speedometer (km/h), Motor Tachometer (RPM), Electrical Power (kW), Battery SOC (%), Pack Current (A), Terminal Voltage (V), G-Force Indicators.
- **Top-Down 2D Track Visualizer:**
  - Real-time car cursor position marker navigating the circuit.
  - Color-coded heatmap switchable by: Speed, Motor Power, Lateral G, and Sectors.
- **Simulation Playback Engine:**
  - Play, Pause, Reset, Lap End buttons.
  - Multiplier speed selector (0.5x, 1x, 2x, 5x, 10x).
  - Time Scrubber Slider: Jump directly to any corner or braking zone.
- **Dynamic Configuration Sidebar:** Live tuning of vehicle mass, aero $C_d$, motor power, battery capacity, tyre grip, and solar irradiance.

---

### Slide 8: Energy Audit, Validation, and Limitations

**Energy & Power Balances (1 Flying Lap = 2,120 m):**
- **Gross Energy Consumed:** $0.224\text{ kWh}$
- **Regenerative Braking Harvest:** $0.016\text{ kWh}$ (~7.1% energy recovered)
- **Solar PV Generation:** $0.015\text{ kWh}$ ($725\text{ W}$ continuous clean generation)
- **Net Energy Consumed:** **0.208 kWh** (Specific efficiency: **98.3 Wh/km**)
- **Battery State of Charge:** Initial $90.00\%$ $\to$ Final $85.55\%$ ($\Delta \text{SOC} = -4.45\%$)

**Validation & Verification (13 Automated Unit Tests):**
- Aerodynamic drag scales strictly with $v^2$ ($R^2 = 1.0$).
- Motor torque and power strictly capped at $75\text{ Nm}$ and $12\text{ kW}$.
- Battery SOC decreases on discharge and increases during regenerative braking.
- Terminal voltage exhibits realistic internal resistance sag under load ($V = V_{\text{ocv}} - IR$).
- Lateral cornering speeds strictly satisfy tyre adhesion limits ($a_y \le \mu g$).

**Engineering Assumptions & Limitations:**
- Planar circuit model (zero elevation gradient).
- Quasi-steady state load transfer (ignores transient roll/pitch damper delays).
- Constant battery/motor operating temperature ($30^\circ\text{C}$).

---

### Slide 9: Conclusion and Future Scope

**Summary of Deliverables:**
- Fully operational Streamlit application: `streamlit run app.py`
- Complete modular physics engine (`vehicle.py`, `motor.py`, `battery.py`, `dynamics.py`)
- Numerical two-pass Kari Motor Speedway simulator (`lap_simulator.py`)
- Verified test suite (`tests/` — 13/13 tests passing)
- Telemetry datasets (`results/sample_lap_telemetry.csv`, `results/lap_summary.json`)
- Comprehensive technical documentation (`README.md`)

**Future Roadmap:**
1. **LIDAR / RTK DGPS Track Ingestion:** Ingest 3D elevation and camber survey data for Kari Speedway.
2. **Thermal Dynamics Model:** Couple motor winding and battery cell lumped thermal models to simulate thermal derating over multi-lap stints.
3. **Solar Track Shadowing:** Incorporate sun azimuth/elevation angles and circuit terrain shading throughout the day.
4. **Hardware-in-the-Loop (HIL):** Stream CAN bus telemetry directly from the physical vehicle into the HELIOS dashboard.

---
**HELIOS Digital Twin — Ready for Demonstration.**

