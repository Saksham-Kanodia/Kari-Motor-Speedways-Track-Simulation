export const DEFAULTS = {
  vehicle_mass: 320,
  drag_coefficient: 0.20,
  frontal_area: 1.15,
  rolling_resistance_coeff: 0.007,
  friction_coefficient: 1.15,
  motor_peak_power_kw: 12,
  motor_peak_torque_nm: 75,
  gear_ratio: 4.2,
  battery_nominal_voltage: 96,
  battery_capacity_ah: 50,
  initial_soc_pct: 90,
  regen_efficiency_pct: 70,
  solar_irradiance_wm2: 850,
  solar_array_area_m2: 4
};

const G = 9.80665;
const AIR_DENSITY = 1.225;
const WHEEL_RADIUS = 0.28;
const DRIVETRAIN_EFFICIENCY = 0.96;
const MOTOR_EFFICIENCY = 0.92;
const MOTOR_MAX_RPM = 5500;
const MAX_BRAKE_FORCE = 3500;
const BATTERY_RESISTANCE = 0.045;
const MAX_DISCHARGE_CURRENT = 140;
const MAX_CHARGE_CURRENT = 70;
const MAX_REGEN_POWER = 7000;
const PV_CELL_EFFICIENCY = 0.22;
const MPPT_EFFICIENCY = 0.97;

export function parseTrackCsv(csv) {
  const lines = csv.trim().split(/\r?\n/);
  const headers = lines.shift().split(",");
  const index = Object.fromEntries(headers.map((name, i) => [name.trim(), i]));
  return lines.map((line) => {
    const cells = line.split(",");
    return {
      distance_m: Number(cells[index.distance_m]),
      x_m: Number(cells[index.x_m]),
      y_m: Number(cells[index.y_m]),
      curvature: Number(cells[index.curvature_rad_m]),
      sector: Number(cells[index.sector])
    };
  }).filter((p) => Number.isFinite(p.distance_m) && Number.isFinite(p.x_m) && Number.isFinite(p.y_m));
}

function motorRpm(speed, gearRatio) {
  if (speed <= 0) return 0;
  return Math.min((speed / WHEEL_RADIUS) * gearRatio * 60 / (2 * Math.PI), MOTOR_MAX_RPM * 1.2);
}

function maxMotorTorque(rpm, params) {
  if (rpm >= MOTOR_MAX_RPM) return 0;
  if (rpm <= 0) return params.motor_peak_torque_nm;
  const omega = rpm * 2 * Math.PI / 60;
  const baseOmega = params.motor_peak_power_kw * 1000 / Math.max(params.motor_peak_torque_nm, 1e-3);
  return omega <= baseOmega ? params.motor_peak_torque_nm : Math.min(params.motor_peak_power_kw * 1000 / omega, params.motor_peak_torque_nm);
}

function tractiveForce(speed, params) {
  const torque = maxMotorTorque(motorRpm(speed, params.gear_ratio), params);
  return torque * params.gear_ratio * DRIVETRAIN_EFFICIENCY / WHEEL_RADIUS;
}

function dragForce(speed, params) {
  return 0.5 * AIR_DENSITY * params.drag_coefficient * params.frontal_area * Math.max(0, speed) ** 2;
}

function rollingForce(speed, params) {
  return speed <= 0.001 ? 0 : params.rolling_resistance_coeff * params.vehicle_mass * G;
}

function lateralAccel(speed, curvature) {
  return speed * speed * curvature;
}

function availableLongitudinalAccel(ay, mu) {
  const maxAccel = mu * G;
  const ratio = Math.min(1, Math.abs(ay) / Math.max(maxAccel, 1e-3));
  return maxAccel * Math.sqrt(Math.max(0, 1 - ratio * ratio));
}

function maxAcceleration(speed, curvature, params) {
  const drag = dragForce(speed, params);
  const rolling = rollingForce(speed, params);
  const grip = availableLongitudinalAccel(lateralAccel(speed, curvature), params.friction_coefficient) * params.vehicle_mass;
  return (Math.min(tractiveForce(speed, params), grip) - drag - rolling) / params.vehicle_mass;
}

function maxDeceleration(speed, curvature, params) {
  const drag = dragForce(speed, params);
  const rolling = rollingForce(speed, params);
  const grip = availableLongitudinalAccel(lateralAccel(speed, curvature), params.friction_coefficient) * params.vehicle_mass;
  return (Math.min(MAX_BRAKE_FORCE, grip) + drag + rolling) / params.vehicle_mass;
}

function ocv(soc, nominalVoltage) {
  const s = Math.min(1, Math.max(0.001, soc / 100));
  return nominalVoltage * (0.88 + 0.17 * s - 0.04 * Math.exp(-12 * s) + 0.02 * s ** 3);
}

function batteryStep(powerDemand, dt, state, params) {
  const voltage = ocv(state.soc, params.battery_nominal_voltage);
  let target;
  if (powerDemand < 0) {
    const maxChargePower = Math.min(MAX_REGEN_POWER, voltage * MAX_CHARGE_CURRENT);
    target = state.soc >= 99.5 ? 0 : Math.max(powerDemand, -maxChargePower);
  } else {
    let maxPower = Math.min(voltage * MAX_DISCHARGE_CURRENT, voltage ** 2 / (4 * BATTERY_RESISTANCE));
    if (state.soc <= 5) maxPower *= state.soc / 5;
    target = Math.min(powerDemand, maxPower);
  }

  const discriminant = voltage ** 2 - 4 * BATTERY_RESISTANCE * target;
  let current = discriminant < 0
    ? voltage / (2 * BATTERY_RESISTANCE)
    : (voltage - Math.sqrt(discriminant)) / (2 * BATTERY_RESISTANCE);
  current = Math.max(-MAX_CHARGE_CURRENT, Math.min(MAX_DISCHARGE_CURRENT, current));
  const terminalVoltage = voltage - current * BATTERY_RESISTANCE;
  const actualPower = terminalVoltage * current;
  state.soc = Math.max(0, Math.min(100, state.soc - current * dt / (params.battery_capacity_ah * 3600) * 100));
  if (actualPower > 0) state.consumed += actualPower * dt;
  else state.recovered += -actualPower * dt;
  return { voltage: terminalVoltage, current, power: actualPower, soc: state.soc };
}

export function simulateLap(params, track) {
  if (!Array.isArray(track) || track.length < 20) throw new Error("Track geometry is missing or invalid. Reload the page and try again.");
  const n = track.length;
  const distances = track.map((p) => p.distance_m);
  const curvature = track.map((p) => p.curvature);
  const vCorner = curvature.map((k) => Math.abs(k) < 1e-4
    ? 60
    : Math.sqrt(params.friction_coefficient * G * 0.98 / Math.abs(k)));

  const vForward = new Float64Array(n);
  vForward[0] = Math.min(vCorner[0], 18);
  for (let i = 0; i < n - 1; i++) {
    const ds = distances[i + 1] - distances[i];
    const a = maxAcceleration(vForward[i], curvature[i], params);
    vForward[i + 1] = Math.min(vCorner[i + 1], Math.sqrt(Math.max(0.1, vForward[i] ** 2 + 2 * a * ds)));
  }

  let vBackward = Float64Array.from(vForward);
  for (let i = n - 1; i > 0; i--) {
    const ds = distances[i] - distances[i - 1];
    const a = maxDeceleration(vBackward[i], curvature[i], params);
    vBackward[i - 1] = Math.min(vBackward[i - 1], Math.sqrt(Math.max(0.1, vBackward[i] ** 2 + 2 * a * ds)));
  }
  let profile = Float64Array.from(vForward, (v, i) => Math.min(v, vBackward[i]));

  vForward[0] = profile[n - 1];
  for (let i = 0; i < n - 1; i++) {
    const ds = distances[i + 1] - distances[i];
    const a = maxAcceleration(vForward[i], curvature[i], params);
    vForward[i + 1] = Math.min(vCorner[i + 1], Math.sqrt(Math.max(0.1, vForward[i] ** 2 + 2 * a * ds)));
  }
  vBackward = Float64Array.from(vForward);
  vBackward[n - 1] = Math.min(vForward[n - 1], profile[0]);
  for (let i = n - 1; i > 0; i--) {
    const ds = distances[i] - distances[i - 1];
    const a = maxDeceleration(vBackward[i], curvature[i], params);
    vBackward[i - 1] = Math.min(vBackward[i - 1], Math.sqrt(Math.max(0.1, vBackward[i] ** 2 + 2 * a * ds)));
  }
  profile = Float64Array.from(vForward, (v, i) => Math.min(v, vBackward[i]));

  const state = {
    soc: params.initial_soc_pct,
    consumed: 0,
    recovered: 0,
    solarJ: 0,
    time: 0
  };
  const telemetry = {
    time_s: [], distance_m: [], x_m: [], y_m: [], sector: [],
    speed_kmh: [], motor_rpm: [], motor_torque_nm: [], motor_mech_power_kw: [],
    motor_elec_power_kw: [], motor_efficiency: [], battery_soc_pct: [],
    battery_current_a: [], battery_voltage_v: [], battery_power_kw: [],
    accel_x_g: [], accel_y_g: [], solar_power_w: [], solar_energy_kwh: [],
    regen_power_kw: [], net_energy_kwh: [], energy_consumed_kwh: [],
    energy_regenerated_kwh: [], curvature: [], f_drive_n: [], f_drag_n: [],
    f_rolling_n: [], f_brake_n: []
  };

  for (let i = 0; i < n; i++) {
    const p = track[i];
    const speed = profile[i];
    const nextSpeed = i < n - 1 ? profile[i + 1] : profile[0];
    const ds = i < n - 1 ? distances[i + 1] - distances[i] : distances[n - 1] - distances[n - 2];
    const averageSpeed = Math.max(0.5 * (speed + nextSpeed), 0.5);
    const dt = ds / averageSpeed;
    const demandedAccel = (nextSpeed ** 2 - speed ** 2) / (2 * ds);
    const drag = dragForce(speed, params);
    const rolling = rollingForce(speed, params);
    const solarPower = params.solar_array_area_m2 * PV_CELL_EFFICIENCY * MPPT_EFFICIENCY * params.solar_irradiance_wm2;
    state.solarJ += solarPower * dt;
    const requiredForce = params.vehicle_mass * demandedAccel + drag + rolling;

    let drive = 0;
    let brake = 0;
    let regenPower = 0;
    let motorTorque = 0;
    let motorMechanicalPower = 0;
    let motorElectricalPower = 0;
    const rpm = motorRpm(speed, params.gear_ratio);
    if (requiredForce >= 0) {
      drive = Math.min(requiredForce, tractiveForce(speed, params));
      motorTorque = (drive * WHEEL_RADIUS) / (params.gear_ratio * DRIVETRAIN_EFFICIENCY);
      const omega = rpm * 2 * Math.PI / 60;
      motorMechanicalPower = motorTorque * omega;
      motorElectricalPower = motorMechanicalPower > 0 ? motorMechanicalPower / MOTOR_EFFICIENCY : 0;
    } else {
      brake = Math.min(-requiredForce, MAX_BRAKE_FORCE);
      regenPower = Math.min(brake * speed * (params.regen_efficiency_pct / 100), MAX_REGEN_POWER);
    }

    const battery = batteryStep(requiredForce >= 0 ? motorElectricalPower - solarPower : -(regenPower + solarPower), dt, state, params);
    const actualAccel = (drive - drag - rolling - brake) / params.vehicle_mass;
    const ay = lateralAccel(speed, p.curvature);

    const push = (key, value) => telemetry[key].push(value);
    push("time_s", state.time);
    push("distance_m", p.distance_m);
    push("x_m", p.x_m);
    push("y_m", p.y_m);
    push("sector", p.sector);
    push("speed_kmh", speed * 3.6);
    push("motor_rpm", rpm);
    push("motor_torque_nm", motorTorque);
    push("motor_mech_power_kw", motorMechanicalPower / 1000);
    push("motor_elec_power_kw", motorElectricalPower / 1000);
    push("motor_efficiency", MOTOR_EFFICIENCY);
    push("battery_soc_pct", battery.soc);
    push("battery_current_a", battery.current);
    push("battery_voltage_v", battery.voltage);
    push("battery_power_kw", battery.power / 1000);
    push("accel_x_g", actualAccel / G);
    push("accel_y_g", ay / G);
    push("solar_power_w", solarPower);
    push("solar_energy_kwh", state.solarJ / 3.6e6);
    push("regen_power_kw", regenPower / 1000);
    push("net_energy_kwh", (state.consumed - state.recovered) / 3.6e6);
    push("energy_consumed_kwh", state.consumed / 3.6e6);
    push("energy_regenerated_kwh", state.recovered / 3.6e6);
    push("curvature", p.curvature);
    push("f_drive_n", drive);
    push("f_drag_n", drag);
    push("f_rolling_n", rolling);
    push("f_brake_n", brake);
    state.time += dt;
  }

  const values = (key) => telemetry[key];
  const max = (key) => Math.max(...values(key));
  const min = (key) => Math.min(...values(key));
  const sectorEnd = (sector) => {
    const indices = telemetry.sector.map((s, i) => s === sector ? i : -1).filter((i) => i >= 0);
    return indices.length ? telemetry.time_s[indices[indices.length - 1]] : 0;
  };
  const lapTime = telemetry.time_s[n - 1];
  const s1 = sectorEnd(1);
  const s2 = sectorEnd(2) - s1;
  const net = telemetry.net_energy_kwh[n - 1];
  const length = distances[n - 1];
  const summary = {
    lap_time_s: lapTime,
    sector_1_s: s1,
    sector_2_s: s2,
    sector_3_s: lapTime - s1 - s2,
    max_speed_kmh: max("speed_kmh"),
    min_speed_kmh: min("speed_kmh"),
    avg_speed_kmh: length / Math.max(lapTime, 1e-6) * 3.6,
    max_long_accel_mps2: max("accel_x_g") * G,
    max_braking_decel_mps2: Math.abs(min("accel_x_g") * G),
    max_lat_accel_mps2: max("accel_y_g") * G,
    max_lat_accel_g: max("accel_y_g"),
    energy_consumed_kwh: telemetry.energy_consumed_kwh[n - 1],
    energy_regenerated_kwh: telemetry.energy_regenerated_kwh[n - 1],
    solar_energy_harvested_kwh: telemetry.solar_energy_kwh[n - 1],
    net_energy_kwh: net,
    efficiency_wh_km: net * 1000 / (length / 1000),
    initial_soc_pct: params.initial_soc_pct,
    final_soc_pct: telemetry.battery_soc_pct[n - 1],
    soc_delta_pct: telemetry.battery_soc_pct[n - 1] - params.initial_soc_pct
  };
  return { telemetry, summary };
}
