# HELIOS — Physics-Based Solar EV Digital Twin & Kari Motor Speedway Simulator

![Python 3](https://img.shields.io/badge/Python-3.14-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.62-red.svg)
![NumPy](https://img.shields.io/badge/NumPy-2.4-brightgreen.svg)
![Plotly](https://img.shields.io/badge/Plotly-7.1-orange.svg)
![Status](https://img.shields.io/badge/Status-Validated-success.svg)

---

## 1. Project Overview & Primary Objectives

**HELIOS** is an end-to-end physics-based digital twin and lap simulator developed for a single-seater high-efficiency Solar Electric Vehicle (Solar EV) racing on **Kari Motor Speedway** (Coimbatore, Tamil Nadu, India).

Unlike static dashboards displaying synthetic numbers, HELIOS implements first-principles vehicle dynamics, electrical powertrain modeling, lithium electrochemical battery state tracking, photovoltaic solar irradiance harvesting, and forward-backward numerical velocity profiling along a continuous 2D parametric track centerline.

### Core Simulation Capabilities:
1. **Longitudinal Dynamics:** Full vehicle resistance resolution ($F_{\text{drive}} - F_{\text{drag}} - F_{\text{rolling}} - F_{\text{gradient}} - F_{\text{brake}}$) based on Newton's second law.
2. **PMSM Electric Motor Model:** Torque saturation up to base speed, constant power field-weakening regime, and rotational cut-off limits.
3. **Electrochemical Battery Model:** Internal resistance equivalent circuit model with non-linear Open-Circuit Voltage ($V_{\text{ocv}}$) curve and coulometric State-of-Charge (SOC) tracking.
4. **Regenerative Braking:** Energy harvesting constrained by motor regen ceilings, tyre grip limits, and battery charge current limits.
5. **Solar Photovoltaic Harvesting:** MPPT-coupled solar PV array model capturing continuous energy harvest based on solar irradiance ($W/m^2$).
6. **Lateral Dynamics & Grip Envelope:** Curvature-dependent cornering limits via tyre adhesion friction circle ($1.15g$ ceiling) and lateral load transfer.
7. **Two-Pass Velocity Profiler:** Forward acceleration and backward braking numerical passes ensuring cyclic track boundary convergence.
8. **Interactive Automotive Telemetry Cockpit:** Streamlit dark telemetry interface with animated car positioning, live HUD gauges, and multi-channel charts.

---

## 2. System Architecture

```text
helios-digital-twin/
│
├── app.py                      # Main Streamlit telemetry dashboard application
├── config.py                   # Centralized vehicle & circuit specifications
├── requirements.txt            # Python dependencies
├── README.md                   # Comprehensive technical documentation
├── presentation_slides.md      # 9-slide technical engineering presentation
│
├── physics_engine/             # First-principles physical models
│   ├── __init__.py
│   ├── vehicle.py              # Longitudinal chassis dynamics, resistance & step solver
│   ├── motor.py                # Electric motor torque/power/RPM limits & efficiency
│   ├── battery.py              # Electrochemical equivalent circuit, OCV & SOC tracker
│   └── dynamics.py             # Lateral acceleration, cornering limits & load transfer
│
├── simulation/                 # Track and numerical simulation engine
│   ├── __init__.py
│   ├── track.py                # Parametric spline centerline model of Kari Motor Speedway
│   ├── lap_simulator.py        # Forward-backward velocity profiler & time integrator
│   └── telemetry.py            # Telemetry manager, snapshot interpolation & CSV export
│
├── visualization/              # UI and visualization components
│   ├── __init__.py
│   ├── dashboard.py            # Automotive dark telemetry HUD components
│   └── plots.py                # Interactive Plotly figures & publication Matplotlib plots
│
├── data/
│   └── track_data.csv          # Discretized 2,120m track centerline & curvature dataset
│
├── results/                    # Generated simulation telemetry and plots
│   ├── sample_lap_telemetry.csv # High-resolution sample lap telemetry
│   ├── lap_summary.json        # Key performance indicators and lap metrics
│   ├── speed_profile.png       # Velocity profile static figure
│   ├── powertrain_telemetry.png# Power and SOC traces
│   └── friction_circle_gg.png  # G-G acceleration diagram
│
└── tests/                      # Automated unit and integration test suite
    ├── test_physics.py         # Motor limits, aero drag, rolling resistance & cornering tests
    ├── test_battery.py         # SOC discharge, regen charging, and voltage sag tests
    └── test_simulation.py      # Circuit distance, lap completion & telemetry validity tests
```

---

## 3. Mathematical & Physics Modelling

### 3.1 Longitudinal Dynamics
Newton's Second Law applied to the vehicle along the longitudinal axis:

$$m \cdot a_x = F_{\text{drive}} - F_{\text{drag}} - F_{\text{rolling}} - F_{\text{gradient}} - F_{\text{braking}}$$

Where:
- **Aerodynamic Drag:**
  $$F_{\text{drag}} = \frac{1}{2} \cdot \rho_{\text{air}} \cdot C_d \cdot A \cdot v^2$$
  *Air density $\rho = 1.225 \text{ kg/m}^3$, Drag Coefficient $C_d = 0.20$, Frontal Area $A = 1.15 \text{ m}^2$.*
- **Rolling Resistance:**
  $$F_{\text{rolling}} = C_{rr} \cdot m \cdot g \cdot \cos(\theta)$$
  *Rolling resistance coefficient $C_{rr} = 0.007$, Vehicle mass $m = 320 \text{ kg}$, $g = 9.80665 \text{ m/s}^2$.*
- **Gradient Resistance:**
  $$F_{\text{gradient}} = m \cdot g \cdot \sin(\theta)$$
  *(Track is assumed planar with nominal zero slope).*

### 3.2 Electric Motor & Drivetrain Model
Motor rotational velocity is mechanically coupled to vehicle linear speed:

$$\omega_{\text{wheel}} = \frac{v}{r_w}, \quad \omega_{\text{motor}} = \omega_{\text{wheel}} \cdot G, \quad \text{RPM} = \omega_{\text{motor}} \cdot \frac{60}{2\pi}$$

Where $r_w = 0.28 \text{ m}$ (wheel radius) and $G = 4.2$ (gear ratio).

The maximum motor torque profile follows a dual-regime characteristic:
1. **Constant Torque Regime ($\omega \le \omega_{\text{base}}$):**
   $$T_{\text{max}}(\omega) = T_{\text{peak}} = 75.0 \text{ Nm}$$
   $$\omega_{\text{base}} = \frac{P_{\text{peak}}}{T_{\text{peak}}} = \frac{12000 \text{ W}}{75 \text{ Nm}} = 160 \text{ rad/s} \quad (\approx 1528 \text{ RPM})$$
2. **Constant Power Regime ($\omega_{\text{base}} < \omega \le \omega_{\text{max}}$):**
   $$T_{\text{max}}(\omega) = \frac{P_{\text{peak}}}{\omega} = \frac{12000 \text{ W}}{\omega}$$
3. **Rotational Cut-off ($\omega > \omega_{\text{max}} = 5500 \text{ RPM}$):**
   $$T_{\text{max}} = 0 \text{ Nm}$$

Tractive force delivered at the tyres:
$$F_{\text{tractive}} = \frac{T_{\text{motor}} \cdot G \cdot \eta_{\text{trans}}}{r_w}$$
*(Transmission efficiency $\eta_{\text{trans}} = 0.96$)*.

### 3.3 Battery & Energy Storage Model
Lithium battery pack architecture ($26S$, $96\text{ V}$ nominal, $50\text{ Ah}$, internal resistance $R_{\text{int}} = 0.045\ \Omega$):
- **Open-Circuit Voltage non-linear function:**
  $$V_{\text{ocv}}(SOC) = V_{\text{nom}} \cdot \left[0.88 + 0.17 s - 0.04 e^{-12s} + 0.02 s^3\right], \quad s = \frac{SOC}{100}$$
- **Terminal Voltage under load:**
  $$V_{\text{term}} = V_{\text{ocv}} - I \cdot R_{\text{int}}$$
- **Current calculation from electrical power demand $P$:**
  $$R_{\text{int}} I^2 - V_{\text{ocv}} I + P = 0 \implies I = \frac{V_{\text{ocv}} - \sqrt{V_{\text{ocv}}^2 - 4 R_{\text{int}} P}}{2 R_{\text{int}}}$$
- **Coulomb Counting SOC Integration:**
  $$SOC(t + \Delta t) = SOC(t) - \frac{I \cdot \Delta t}{Q_{\text{cap}} \cdot 3600} \times 100\%$$
- **Regenerative Braking:** Recovered power $P_{\text{regen}} = \min(F_{\text{brake}} \cdot v \cdot \eta_{\text{regen}}, P_{\text{regen,max}})$.
- **Solar Harvesting:** $P_{\text{solar}} = A_{pv} \cdot \eta_{pv} \cdot \eta_{\text{mppt}} \cdot G_{\text{solar}} = 4.0 \cdot 0.22 \cdot 0.97 \cdot 850 \approx 725.5 \text{ W}$.

### 3.4 Lateral Dynamics & Cornering Limits
- **Curvature:**
  $$\kappa(s) = \frac{x'(s) y''(s) - y'(s) x''(s)}{\left(x'(s)^2 + y'(s)^2\right)^{3/2}}$$
- **Lateral Acceleration:**
  $$a_y(s) = v^2 \cdot \kappa(s)$$
- **Cornering Speed Constraint (Tyre Grip Envelope):**
  $$v_{\text{corner,max}}(s) = \sqrt{\frac{\mu \cdot g \cdot 0.98}{\max(|\kappa(s)|, 10^{-6})}}$$
- **Friction Circle (Kamm's Adhesion Ellipse):**
  $$\left(\frac{a_x}{\mu g}\right)^2 + \left(\frac{a_y}{\mu g}\right)^2 \le 1.0 \implies a_{x,\text{available}} = \mu g \sqrt{\max\left(0, 1 - \left(\frac{a_y}{\mu g}\right)^2\right)}$$

---

## 4. Kari Motor Speedway Circuit Modelling

- **Location:** Chettipalayam, Coimbatore, Tamil Nadu, India.
- **Circuit Length:** $2,120 \text{ meters}$.
- **Turns:** 14 Turns, anti-clockwise direction.
- **Sector Division:**
  - **Sector 1 (0 to 678 m):** Start/Finish Straight ($500\text{ m}$), T1 & T2 fast chicane, T3-T4 entry complex.
  - **Sector 2 (678 to 1441 m):** T5 Hairpin ($R \approx 22\text{ m}$ - slowest apex on track), short burst straight, T6-T7 chicane, T8-T10 technical infield bends.
  - **Sector 3 (1441 to 2120 m):** T11-T12 sweeping back straight bends, T13-T14 parabolic final corner leading back onto the main straight.

> **Engineering Notice:** The circuit path is an analytical parametric cubic spline constructed from published track layouts, corner radii, and total circuit length ($2,120\text{ m}$). It is clearly labeled as an approximate mathematical representation and can be substituted with surveyed DGPS/RTK coordinates via `data/track_data.csv`.

---

## 5. Numerical Lap Simulation Profile (Two-Pass Solver)

1. **Step 1: Discretization:** The circuit centerline is sampled at uniform resolution $\Delta s = 2.0\text{ m}$ ($1,060\text{ points}$).
2. **Step 2: Cornering Velocity Limit:** Evaluate $v_{\text{corner}}[i]$ based on local curvature $\kappa[i]$ and tyre grip.
3. **Step 3: Forward Acceleration Pass:** Starting from corner exit speed, integrate $v_{i+1} = \min(v_{\text{corner}}[i+1], \sqrt{v_i^2 + 2 a_{\text{accel}} \Delta s})$, where $a_{\text{accel}}$ considers motor torque/power limits, aero drag, and available tyre friction.
4. **Step 4: Backward Braking Pass:** Starting from track end and corner apexes, integrate backwards $v_{i-1} = \min(v_{i-1}, \sqrt{v_i^2 + 2 a_{\text{decel}} \Delta s})$ to enforce braking zones.
5. **Step 5: Cyclic Convergence:** Re-run boundary conditions to guarantee seamless velocity continuity across the Start/Finish line for a flying lap.
6. **Step 6: Time Integration:** Evaluate $\Delta t = \frac{\Delta s}{v_{\text{avg}}}$, step the vehicle battery, motor, and solar physics models, and record the full telemetry stream.

---

## 6. Simulation Results & Performance Summary

Based on baseline configuration ($m = 320\text{ kg}$, $C_d = 0.20$, $A = 1.15\text{ m}^2$, $P_{\text{peak}} = 12\text{ kW}$, $\mu = 1.15$, $G_{\text{solar}} = 850\text{ W/m}^2$):

| Parameter | Simulated Value | Unit | Engineering Note |
|---|---|---|---|
| **Lap Completion Time** | **73.93** | s | ~1 min 13.93s flying lap |
| **Sector 1 Time** | 23.81 | s | High-speed main straight + T1/T2 |
| **Sector 2 Time** | 28.95 | s | Technical infield + T5 Hairpin |
| **Sector 3 Time** | 21.16 | s | Sweepers + Parabolic curve |
| **Maximum Velocity** | **129.2** | km/h | End of 500m main straight |
| **Minimum Velocity** | **51.4** | km/h | T5 Hairpin apex |
| **Average Velocity** | **103.1** | km/h | High-efficiency racing pace |
| **Peak Longitudinal Accel** | **+2.31** | $m/s^2$ (+0.24 g) | Motor tractive force limit |
| **Peak Braking Decel** | **-11.47** | $m/s^2$ (-1.17 g) | Friction circle + aero drag |
| **Peak Lateral Accel** | **11.05** | $m/s^2$ (1.13 g) | Cornering limit ($\mu \times 0.98$) |
| **Gross Energy Consumed** | 0.224 | kWh | Battery discharge |
| **Regen Energy Recovered** | 0.016 | kWh | ~7.1% kinetic energy recovery |
| **Solar Energy Harvested** | 0.015 | kWh | Direct solar PV generation |
| **Net Energy Consumption** | **0.208** | kWh | Net battery draw |
| **Specific Energy Consumption**| **98.3** | Wh/km | High efficiency solar EV benchmark |
| **Initial Battery SOC** | 90.00 | % | Configured start |
| **Final Battery SOC** | 85.55 | % | -4.45% per qualifying lap |

---

## 7. Installation & Quickstart

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Pip package manager

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run Unit Tests
```bash
python -m unittest discover tests
```
*Expected: 13 tests passed cleanly.*

### Step 3: Launch the Interactive Dashboard
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 8. Dashboard Controls & Features Guide

- **Sidebar Sliders:** Modify vehicle mass, drag coefficient, frontal area, motor power, battery capacity, tyre grip, and solar irradiance. The digital twin automatically updates the lap profile.
- **Simulation Playback:**
  - `Play / Pause`: Animated car movement around Kari Motor Speedway.
  - `Speed Multiplier`: Accelerate playback (0.5x, 1x, 2x, 5x, 10x).
  - `Time Scrubber Slider`: Seek to any point in the lap to inspect instantaneous telemetry.
- **Track Heatmap Selector:** Color the track centerline by Speed (km/h), Motor Power (kW), Lateral Accel (g), or Circuit Sectors.
- **Telemetry HUD:** Monospace automotive gauges displaying real-time vehicle speed, motor RPM, motor power, battery voltage, current, SOC, lateral/longitudinal g-forces, and net energy.
- **Analysis Tabs:**
  1. *Powertrain & Battery:* Motor RPM, Power, Battery SOC, Current, and Regen traces.
  2. *Vehicle Dynamics:* G-G friction circle diagram and longitudinal/lateral acceleration.
  3. *Energy & Forces:* Energy accumulation and forces breakdown ($F_{\text{drive}}, F_{\text{drag}}, F_{\text{rolling}}, F_{\text{brake}}$).
  4. *Performance Summary:* Lap split times, energy audit, and kinematic limits.
  5. *Raw Telemetry & Export:* Data preview and one-click **CSV Download**.

---

## 9. Engineering Assumptions & Limitations

1. **Provisional Vehicle Specifications:** Vehicle mass ($320\text{ kg}$), motor capacity ($12\text{ kW}$ peak), and aerodynamic parameters ($C_d = 0.20$) represent typical single-seater solar racing prototypes (e.g. World Solar Challenge / Formula Bharat Electric specifications) and are not measured physical dynamometer data of a specific production chassis.
2. **Track Geometry:** The circuit centerline is reconstructed mathematically using published turn radii and layout maps. Elevation changes are treated as planar (zero gradient).
3. **Quasi-Steady State Model:** The forward-backward velocity solver assumes quasi-steady state tire load and ignores transient suspension pitch and roll dynamics.
4. **Thermal Effects:** Battery and motor internal resistances are assumed constant at nominal ambient temperature ($30^\circ\text{C}$). Thermal derating is not modeled.

