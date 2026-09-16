// JS port of training/simulators/industrial_fault_simulator.py — same exact
// logic, ported so the Node backend can run it in-process, without shelling
// out to `python3` (which Render's Node-native runtime does not provide;
// Render's native runtimes are separate, isolated environments per
// language — there's no guarantee a Python interpreter exists inside a
// service running as `runtime: node`).
//
// The Python file remains the canonical reference/testable version for
// local experimentation (see training/training_loop.py) — this file is
// what actually runs in production.

const COMPONENTS = ['bearing', 'belt', 'motor', 'sensor_calibration'];

const SYMPTOM_PROFILES = {
  bearing:            { vibration_high: 0.9, temperature_high: 0.6, noise_abnormal: 0.8, rpm_unstable: 0.3 },
  belt:               { vibration_high: 0.4, rpm_unstable: 0.85, noise_abnormal: 0.5, temperature_high: 0.1 },
  motor:              { temperature_high: 0.9, rpm_unstable: 0.5, power_draw_high: 0.85, vibration_high: 0.2 },
  sensor_calibration: { rpm_unstable: 0.2, power_draw_high: 0.1, vibration_high: 0.1, temperature_high: 0.15 },
};
const ALL_SYMPTOMS = ['vibration_high', 'temperature_high', 'noise_abnormal', 'rpm_unstable', 'power_draw_high'];

function sampleIntervention() {
  return { failed_component: COMPONENTS[Math.floor(Math.random() * COMPONENTS.length)] };
}

function generateObservations(intervention) {
  const profile = SYMPTOM_PROFILES[intervention.failed_component];
  const observations = {};
  for (const symptom of ALL_SYMPTOMS) {
    const prob = profile[symptom] ?? 0.05;
    observations[symptom] = Math.random() < prob;
  }
  return observations;
}

function verifyProposedStructure(proposed, intervention) {
  if (!proposed || typeof proposed !== 'object' || !('failed_component' in proposed)) return 0.0;
  const proposedComponent = proposed.failed_component;
  const trueComponent = intervention.failed_component;
  if (proposedComponent === trueComponent) return 1.0;

  const trueProfile = SYMPTOM_PROFILES[trueComponent] || {};
  const proposedProfile = SYMPTOM_PROFILES[proposedComponent] || {};
  let overlap = 0, total = 0;
  for (const s of ALL_SYMPTOMS) {
    overlap += Math.min(trueProfile[s] || 0, proposedProfile[s] || 0);
    total += trueProfile[s] || 0;
  }
  return total > 0 ? Math.round((0.3 * (overlap / total)) * 1000) / 1000 : 0.0;
}

// A simple heuristic proposer — same fallback logic as training_loop.py's
// offline path (no API key needed): guess whichever component's symptom
// profile best matches the observed symptoms present.
function proposeStructureHeuristic(observations) {
  const present = ALL_SYMPTOMS.filter(s => observations[s]);
  if (present.length === 0) return { failed_component: COMPONENTS[Math.floor(Math.random() * COMPONENTS.length)] };
  let best = COMPONENTS[0], bestScore = -1;
  for (const c of COMPONENTS) {
    const score = present.reduce((sum, s) => sum + (SYMPTOM_PROFILES[c][s] || 0), 0);
    if (score > bestScore) { bestScore = score; best = c; }
  }
  return { failed_component: best };
}

function generateScenarios(count) {
  const out = [];
  for (let i = 0; i < count; i++) {
    const intervention = sampleIntervention();
    out.push({ hidden_intervention: intervention, observations: generateObservations(intervention) });
  }
  return out;
}

function runSingleScenario(observations, hiddenIntervention) {
  const proposed = proposeStructureHeuristic(observations);
  const reward = verifyProposedStructure(proposed, hiddenIntervention);
  return { proposed, reward };
}

module.exports = {
  generateScenarios, runSingleScenario, sampleIntervention, generateObservations,
  verifyProposedStructure, proposeStructureHeuristic, COMPONENTS, ALL_SYMPTOMS, SYMPTOM_PROFILES,
};
