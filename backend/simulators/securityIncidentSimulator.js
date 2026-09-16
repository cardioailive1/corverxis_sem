// Security Incident Investigation simulator — reconstruct the true attack
// vector behind a breach from log signals, rather than a plausible guess.

const ATTACK_VECTORS = ['phishing_credential_theft', 'unpatched_cve_exploit', 'insider_threat', 'supply_chain_compromise', 'brute_force_login'];

const SIGNAL_PROFILES = {
  phishing_credential_theft: { unusual_login_location: 0.8, after_hours_access: 0.5, multiple_failed_logins: 0.15, privilege_escalation_event: 0.3, new_admin_account_created: 0.1, outbound_data_transfer_spike: 0.35, known_malware_signature: 0.05 },
  unpatched_cve_exploit:     { known_malware_signature: 0.7, privilege_escalation_event: 0.75, outbound_data_transfer_spike: 0.4, unusual_login_location: 0.2, after_hours_access: 0.3, multiple_failed_logins: 0.05, new_admin_account_created: 0.2 },
  insider_threat:            { outbound_data_transfer_spike: 0.75, after_hours_access: 0.7, unusual_login_location: 0.1, privilege_escalation_event: 0.2, new_admin_account_created: 0.1, multiple_failed_logins: 0.02, known_malware_signature: 0.02 },
  supply_chain_compromise:   { known_malware_signature: 0.6, new_admin_account_created: 0.45, privilege_escalation_event: 0.55, outbound_data_transfer_spike: 0.5, unusual_login_location: 0.15, after_hours_access: 0.2, multiple_failed_logins: 0.03 },
  brute_force_login:         { multiple_failed_logins: 0.9, unusual_login_location: 0.5, after_hours_access: 0.4, privilege_escalation_event: 0.1, outbound_data_transfer_spike: 0.1, new_admin_account_created: 0.05, known_malware_signature: 0.02 },
};
const ALL_SIGNALS = ['unusual_login_location', 'privilege_escalation_event', 'outbound_data_transfer_spike', 'known_malware_signature', 'after_hours_access', 'multiple_failed_logins', 'new_admin_account_created'];

function sampleIntervention() { return { attack_vector: ATTACK_VECTORS[Math.floor(Math.random() * ATTACK_VECTORS.length)] }; }
function generateObservations(intervention) {
  const profile = SIGNAL_PROFILES[intervention.attack_vector];
  const observations = {};
  for (const s of ALL_SIGNALS) observations[s] = Math.random() < (profile[s] ?? 0.03);
  return observations;
}
function verifyProposedStructure(proposed, intervention) {
  if (!proposed || typeof proposed !== 'object' || !('attack_vector' in proposed)) return 0.0;
  if (proposed.attack_vector === intervention.attack_vector) return 1.0;
  const trueProfile = SIGNAL_PROFILES[intervention.attack_vector] || {};
  const proposedProfile = SIGNAL_PROFILES[proposed.attack_vector] || {};
  let overlap = 0, total = 0;
  for (const s of ALL_SIGNALS) { overlap += Math.min(trueProfile[s] || 0, proposedProfile[s] || 0); total += trueProfile[s] || 0; }
  return total > 0 ? Math.round((0.3 * (overlap / total)) * 1000) / 1000 : 0.0;
}
function proposeStructureHeuristic(observations) {
  const present = ALL_SIGNALS.filter(s => observations[s]);
  if (present.length === 0) return { attack_vector: ATTACK_VECTORS[Math.floor(Math.random() * ATTACK_VECTORS.length)] };
  let best = ATTACK_VECTORS[0], bestScore = -1;
  for (const c of ATTACK_VECTORS) {
    const score = present.reduce((sum, s) => sum + (SIGNAL_PROFILES[c][s] || 0), 0);
    if (score > bestScore) { bestScore = score; best = c; }
  }
  return { attack_vector: best };
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
module.exports = { generateScenarios, runSingleScenario, sampleIntervention, generateObservations, verifyProposedStructure, proposeStructureHeuristic, ATTACK_VECTORS, ALL_SIGNALS, SIGNAL_PROFILES };
