// Medical Diagnostics simulator — determine the actual condition behind a
// patient's symptoms, verified against known disease-progression patterns.
// Same shape as industrialFaultSimulator.js: hidden intervention (the real
// condition) -> noisy observed symptoms -> verify a proposed diagnosis.

const CONDITIONS = ['influenza', 'bacterial_pneumonia', 'covid19', 'common_cold', 'allergic_rhinitis'];

const SYMPTOM_PROFILES = {
  influenza:           { fever_high: 0.85, body_aches: 0.9, fatigue: 0.8, cough_dry: 0.5, sore_throat: 0.4, sneezing: 0.1, loss_of_taste_smell: 0.05, shortness_of_breath: 0.15 },
  bacterial_pneumonia: { fever_high: 0.9, cough_productive: 0.85, shortness_of_breath: 0.7, fatigue: 0.6, body_aches: 0.3, sore_throat: 0.1, sneezing: 0.05, loss_of_taste_smell: 0.05 },
  covid19:             { fever_high: 0.6, fatigue: 0.75, body_aches: 0.5, loss_of_taste_smell: 0.55, cough_dry: 0.5, shortness_of_breath: 0.35, sore_throat: 0.3, sneezing: 0.1 },
  common_cold:         { sneezing: 0.85, sore_throat: 0.6, cough_dry: 0.4, fatigue: 0.3, fever_high: 0.1, body_aches: 0.15, shortness_of_breath: 0.02, loss_of_taste_smell: 0.02 },
  allergic_rhinitis:   { sneezing: 0.9, sore_throat: 0.15, fatigue: 0.2, fever_high: 0.01, cough_dry: 0.2, body_aches: 0.02, shortness_of_breath: 0.1, loss_of_taste_smell: 0.02 },
};
const ALL_SYMPTOMS = ['fever_high', 'cough_productive', 'cough_dry', 'shortness_of_breath', 'sore_throat', 'body_aches', 'sneezing', 'loss_of_taste_smell', 'fatigue'];

function sampleIntervention() {
  return { condition: CONDITIONS[Math.floor(Math.random() * CONDITIONS.length)] };
}
function generateObservations(intervention) {
  const profile = SYMPTOM_PROFILES[intervention.condition];
  const observations = {};
  for (const s of ALL_SYMPTOMS) observations[s] = Math.random() < (profile[s] ?? 0.03);
  return observations;
}
function verifyProposedStructure(proposed, intervention) {
  if (!proposed || typeof proposed !== 'object' || !('condition' in proposed)) return 0.0;
  if (proposed.condition === intervention.condition) return 1.0;
  const trueProfile = SYMPTOM_PROFILES[intervention.condition] || {};
  const proposedProfile = SYMPTOM_PROFILES[proposed.condition] || {};
  let overlap = 0, total = 0;
  for (const s of ALL_SYMPTOMS) { overlap += Math.min(trueProfile[s] || 0, proposedProfile[s] || 0); total += trueProfile[s] || 0; }
  return total > 0 ? Math.round((0.3 * (overlap / total)) * 1000) / 1000 : 0.0;
}
function proposeStructureHeuristic(observations) {
  const present = ALL_SYMPTOMS.filter(s => observations[s]);
  if (present.length === 0) return { condition: CONDITIONS[Math.floor(Math.random() * CONDITIONS.length)] };
  let best = CONDITIONS[0], bestScore = -1;
  for (const c of CONDITIONS) {
    const score = present.reduce((sum, s) => sum + (SYMPTOM_PROFILES[c][s] || 0), 0);
    if (score > bestScore) { bestScore = score; best = c; }
  }
  return { condition: best };
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
  return { proposed, reward: verifyProposedStructure(proposed, hiddenIntervention) };
}
module.exports = { generateScenarios, runSingleScenario, sampleIntervention, generateObservations, verifyProposedStructure, proposeStructureHeuristic, CONDITIONS, ALL_SYMPTOMS, SYMPTOM_PROFILES };
