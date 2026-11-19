// production-incident-rootcause simulator. Causes, signals and probabilities live in domains_spec.json (shared with the
// Python training simulators); see specSimulator.js.
module.exports = require("./specSimulator.js").make("production-incident-rootcause", "ROOT_CAUSES");
