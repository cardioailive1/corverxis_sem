// safety-incident-analysis simulator. Causes, signals and probabilities live in domains_spec.json (shared with the
// Python training simulators); see specSimulator.js.
module.exports = require("./specSimulator.js").make("safety-incident-analysis", "INCIDENT_CAUSES");
