// Generic simulator engine driven by domains_spec.json — the same spec the Python training
// simulators read (training/simulators/build_spec.py generates both copies).
// Each domain: hidden cause -> noisy binary signals -> verify a proposed cause.
const SPEC = Object.fromEntries(require('./domains_spec.json').domains.map(d => [d.slug, d]));

const pick = arr => arr[Math.floor(Math.random() * arr.length)];

function make(slug, listName) {
  const d = SPEC[slug];
  if (!d) throw new Error(`No domain '${slug}' in domains_spec.json`);
  const { key, causes, signals, profiles, default_p: dp } = d;

  const sampleIntervention = () => ({ [key]: pick(causes) });
  const generateObservations = intervention => {
    const p = profiles[intervention[key]];
    const obs = {};
    for (const s of signals) obs[s] = Math.random() < (p[s] ?? dp);
    return obs;
  };
  const verifyProposedStructure = (proposed, intervention) => {
    if (!proposed || typeof proposed !== 'object' || !(key in proposed)) return 0.0;
    if (proposed[key] === intervention[key]) return 1.0;
    const tp = profiles[intervention[key]] || {}, pp = profiles[proposed[key]] || {};
    let overlap = 0, total = 0;
    for (const s of signals) { overlap += Math.min(tp[s] || 0, pp[s] || 0); total += tp[s] || 0; }
    return total > 0 ? Math.round(0.3 * (overlap / total) * 1000) / 1000 : 0.0;
  };
  // Simple baseline used by the Lab's training-run demo: the cause whose profile weights best cover the present signals.
  const proposeStructureHeuristic = observations => {
    const present = signals.filter(s => observations[s]);
    if (!present.length) return { [key]: pick(causes) };
    let best = causes[0], bestScore = -1;
    for (const c of causes) {
      const score = present.reduce((sum, s) => sum + (profiles[c][s] || 0), 0);
      if (score > bestScore) { bestScore = score; best = c; }
    }
    return { [key]: best };
  };
  const generateScenarios = count => Array.from({ length: count }, () => {
    const intervention = sampleIntervention();
    return { hidden_intervention: intervention, observations: generateObservations(intervention) };
  });
  const runSingleScenario = (observations, hidden) => {
    const proposed = proposeStructureHeuristic(observations);
    return { proposed, reward: verifyProposedStructure(proposed, hidden) };
  };
  return { generateScenarios, runSingleScenario, sampleIntervention, generateObservations, verifyProposedStructure,
    proposeStructureHeuristic, [listName]: causes, ALL_SYMPTOMS: signals, ALL_SIGNALS: signals,
    SYMPTOM_PROFILES: profiles, SIGNAL_PROFILES: profiles, SLUG: slug, KEY: key };
}

module.exports = { make, SPEC, slugs: () => Object.keys(SPEC) };
