// supply-chain-disruption simulator. Causes, signals and probabilities live in domains_spec.json (shared with the
// Python training simulators); see specSimulator.js.
module.exports = require("./specSimulator.js").make("supply-chain-disruption", "DISRUPTION_CAUSES");
