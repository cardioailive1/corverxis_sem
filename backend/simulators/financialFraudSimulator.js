// Financial Fraud/Anomaly Investigation simulator — the actual cause behind
// an unusual transaction pattern, not just a flagged correlation. Includes
// a genuine "not fraud" class — real fraud detection has to distinguish
// fraud from legitimate-but-unusual behavior, not just classify among
// fraud types.

const CAUSES = ['stolen_card_testing', 'account_takeover', 'synthetic_identity', 'merchant_collusion', 'legitimate_unusual_purchase'];

const SIGNAL_PROFILES = {
  stolen_card_testing:         { rapid_small_transactions: 0.9, velocity_spike: 0.85, new_shipping_address: 0.2, device_fingerprint_mismatch: 0.3, high_risk_merchant_category: 0.4, geo_mismatch: 0.3 },
  account_takeover:            { device_fingerprint_mismatch: 0.85, geo_mismatch: 0.7, new_shipping_address: 0.6, velocity_spike: 0.4, rapid_small_transactions: 0.15, high_risk_merchant_category: 0.2 },
  synthetic_identity:          { new_shipping_address: 0.7, high_risk_merchant_category: 0.3, velocity_spike: 0.25, device_fingerprint_mismatch: 0.2, rapid_small_transactions: 0.1, geo_mismatch: 0.15 },
  merchant_collusion:          { high_risk_merchant_category: 0.8, rapid_small_transactions: 0.3, velocity_spike: 0.3, new_shipping_address: 0.05, device_fingerprint_mismatch: 0.1, geo_mismatch: 0.1 },
  legitimate_unusual_purchase: { new_shipping_address: 0.25, geo_mismatch: 0.2, velocity_spike: 0.1, high_risk_merchant_category: 0.1, rapid_small_transactions: 0.03, device_fingerprint_mismatch: 0.05 },
};
const ALL_SIGNALS = ['rapid_small_transactions', 'new_shipping_address', 'device_fingerprint_mismatch', 'velocity_spike', 'high_risk_merchant_category', 'geo_mismatch'];

function sampleIntervention() { return { cause: CAUSES[Math.floor(Math.random() * CAUSES.length)] }; }
function generateObservations(intervention) {
  const profile = SIGNAL_PROFILES[intervention.cause];
  const observations = {};
  for (const s of ALL_SIGNALS) observations[s] = Math.random() < (profile[s] ?? 0.02);
  return observations;
}
function verifyProposedStructure(proposed, intervention) {
  if (!proposed || typeof proposed !== 'object' || !('cause' in proposed)) return 0.0;
  if (proposed.cause === intervention.cause) return 1.0;
  const trueProfile = SIGNAL_PROFILES[intervention.cause] || {};
  const proposedProfile = SIGNAL_PROFILES[proposed.cause] || {};
  let overlap = 0, total = 0;
  for (const s of ALL_SIGNALS) { overlap += Math.min(trueProfile[s] || 0, proposedProfile[s] || 0); total += trueProfile[s] || 0; }
  return total > 0 ? Math.round((0.3 * (overlap / total)) * 1000) / 1000 : 0.0;
}
function proposeStructureHeuristic(observations) {
  const present = ALL_SIGNALS.filter(s => observations[s]);
  if (present.length === 0) return { cause: 'legitimate_unusual_purchase' };   // no red flags -> assume legitimate, matching real-world fraud triage
  let best = CAUSES[0], bestScore = -1;
  for (const c of CAUSES) {
    const score = present.reduce((sum, s) => sum + (SIGNAL_PROFILES[c][s] || 0), 0);
    if (score > bestScore) { bestScore = score; best = c; }
  }
  return { cause: best };
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
module.exports = { generateScenarios, runSingleScenario, sampleIntervention, generateObservations, verifyProposedStructure, proposeStructureHeuristic, CAUSES, ALL_SIGNALS, SIGNAL_PROFILES };
