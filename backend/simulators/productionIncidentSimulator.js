// Production Incident Root-Causing simulator — what actually broke and why,
// checked against replay/simulation rather than a first hypothesis.

const ROOT_CAUSES = ['bad_deploy', 'database_connection_pool_exhaustion', 'third_party_api_outage', 'traffic_spike_ddos', 'memory_leak'];

const SIGNAL_PROFILES = {
  bad_deploy:                          { deploy_within_last_hour: 0.9, error_rate_spike: 0.75, latency_increase: 0.4, upstream_5xx_errors: 0.3, database_timeout_errors: 0.15, cpu_usage_high: 0.2, memory_usage_climbing: 0.1 },
  database_connection_pool_exhaustion: { database_timeout_errors: 0.9, latency_increase: 0.7, error_rate_spike: 0.5, deploy_within_last_hour: 0.1, cpu_usage_high: 0.2, memory_usage_climbing: 0.15, upstream_5xx_errors: 0.1 },
  third_party_api_outage:              { upstream_5xx_errors: 0.85, latency_increase: 0.6, error_rate_spike: 0.55, deploy_within_last_hour: 0.05, database_timeout_errors: 0.1, cpu_usage_high: 0.1, memory_usage_climbing: 0.05 },
  traffic_spike_ddos:                  { cpu_usage_high: 0.85, latency_increase: 0.75, error_rate_spike: 0.6, database_timeout_errors: 0.3, memory_usage_climbing: 0.2, deploy_within_last_hour: 0.05, upstream_5xx_errors: 0.15 },
  memory_leak:                         { memory_usage_climbing: 0.9, latency_increase: 0.5, error_rate_spike: 0.35, cpu_usage_high: 0.25, deploy_within_last_hour: 0.1, database_timeout_errors: 0.1, upstream_5xx_errors: 0.05 },
};
const ALL_SIGNALS = ['error_rate_spike', 'latency_increase', 'deploy_within_last_hour', 'database_timeout_errors', 'cpu_usage_high', 'memory_usage_climbing', 'upstream_5xx_errors'];

function sampleIntervention() { return { root_cause: ROOT_CAUSES[Math.floor(Math.random() * ROOT_CAUSES.length)] }; }
function generateObservations(intervention) {
  const profile = SIGNAL_PROFILES[intervention.root_cause];
  const observations = {};
  for (const s of ALL_SIGNALS) observations[s] = Math.random() < (profile[s] ?? 0.03);
  return observations;
}
function verifyProposedStructure(proposed, intervention) {
  if (!proposed || typeof proposed !== 'object' || !('root_cause' in proposed)) return 0.0;
  if (proposed.root_cause === intervention.root_cause) return 1.0;
  const trueProfile = SIGNAL_PROFILES[intervention.root_cause] || {};
  const proposedProfile = SIGNAL_PROFILES[proposed.root_cause] || {};
  let overlap = 0, total = 0;
  for (const s of ALL_SIGNALS) { overlap += Math.min(trueProfile[s] || 0, proposedProfile[s] || 0); total += trueProfile[s] || 0; }
  return total > 0 ? Math.round((0.3 * (overlap / total)) * 1000) / 1000 : 0.0;
}
function proposeStructureHeuristic(observations) {
  const present = ALL_SIGNALS.filter(s => observations[s]);
  if (present.length === 0) return { root_cause: ROOT_CAUSES[Math.floor(Math.random() * ROOT_CAUSES.length)] };
  let best = ROOT_CAUSES[0], bestScore = -1;
  for (const c of ROOT_CAUSES) {
    const score = present.reduce((sum, s) => sum + (SIGNAL_PROFILES[c][s] || 0), 0);
    if (score > bestScore) { bestScore = score; best = c; }
  }
  return { root_cause: best };
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
module.exports = { generateScenarios, runSingleScenario, sampleIntervention, generateObservations, verifyProposedStructure, proposeStructureHeuristic, ROOT_CAUSES, ALL_SIGNALS, SIGNAL_PROFILES };
