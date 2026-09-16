// Scientific Discovery simulator — propose the real causal mechanism behind
// an experimental result, verified against further simulated experiments.
// Genuinely important that "genuine_novel_effect" isn't the default guess —
// most surprising results in real science turn out to be artifacts or
// confounds, not real discoveries, and a good verifier should reflect that.

const MECHANISMS = ['catalyst_effect', 'confounding_variable', 'measurement_artifact', 'genuine_novel_effect', 'temperature_dependency'];

const SIGNAL_PROFILES = {
  catalyst_effect:        { dose_response_relationship: 0.85, result_reproducible: 0.8, effect_size_large: 0.6, correlates_with_control_variable: 0.1, instrument_calibration_drift: 0.05 },
  confounding_variable:   { correlates_with_control_variable: 0.9, result_reproducible: 0.6, dose_response_relationship: 0.3, effect_size_large: 0.4, instrument_calibration_drift: 0.1 },
  measurement_artifact:   { instrument_calibration_drift: 0.85, result_reproducible: 0.2, correlates_with_control_variable: 0.15, dose_response_relationship: 0.1, effect_size_large: 0.3 },
  genuine_novel_effect:   { result_reproducible: 0.9, dose_response_relationship: 0.7, effect_size_large: 0.55, correlates_with_control_variable: 0.05, instrument_calibration_drift: 0.03 },
  temperature_dependency: { dose_response_relationship: 0.5, result_reproducible: 0.75, correlates_with_control_variable: 0.4, effect_size_large: 0.35, instrument_calibration_drift: 0.1 },
};
const ALL_SIGNALS = ['result_reproducible', 'correlates_with_control_variable', 'effect_size_large', 'dose_response_relationship', 'instrument_calibration_drift'];

function sampleIntervention() { return { mechanism: MECHANISMS[Math.floor(Math.random() * MECHANISMS.length)] }; }
function generateObservations(intervention) {
  const profile = SIGNAL_PROFILES[intervention.mechanism];
  const observations = {};
  for (const s of ALL_SIGNALS) observations[s] = Math.random() < (profile[s] ?? 0.05);
  return observations;
}
function verifyProposedStructure(proposed, intervention) {
  if (!proposed || typeof proposed !== 'object' || !('mechanism' in proposed)) return 0.0;
  if (proposed.mechanism === intervention.mechanism) return 1.0;
  const trueProfile = SIGNAL_PROFILES[intervention.mechanism] || {};
  const proposedProfile = SIGNAL_PROFILES[proposed.mechanism] || {};
  let overlap = 0, total = 0;
  for (const s of ALL_SIGNALS) { overlap += Math.min(trueProfile[s] || 0, proposedProfile[s] || 0); total += trueProfile[s] || 0; }
  return total > 0 ? Math.round((0.3 * (overlap / total)) * 1000) / 1000 : 0.0;
}
function proposeStructureHeuristic(observations) {
  const present = ALL_SIGNALS.filter(s => observations[s]);
  if (present.length === 0) return { mechanism: 'measurement_artifact' };   // no signal present -> most likely just noise/artifact, not a real effect
  let best = MECHANISMS[0], bestScore = -1;
  for (const c of MECHANISMS) {
    const score = present.reduce((sum, s) => sum + (SIGNAL_PROFILES[c][s] || 0), 0);
    if (score > bestScore) { bestScore = score; best = c; }
  }
  return { mechanism: best };
}
function generateScenarios(count) {
  const out = [];
  for (let i = 0; i < count; i++) { const intervention = sampleIntervention(); out.push({ hidden_intervention: intervention, observations: generateObservations(intervention) }); }
  return out;
}
function runSingleScenario(observations, hiddenIntervention) {
  const proposed = proposeStructureHeuristic(observations);
  return { proposed, reward: verifyProposedStructure(proposed, hiddenIntervention) };
}
module.exports = { generateScenarios, runSingleScenario, sampleIntervention, generateObservations, verifyProposedStructure, proposeStructureHeuristic, MECHANISMS, ALL_SIGNALS, SIGNAL_PROFILES };
