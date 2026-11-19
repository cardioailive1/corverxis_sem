"""production-incident-rootcause simulator. Thin wrapper: the causes, signals and probabilities live in domains_spec.json
(authored in build_spec.py) and are shared with the Node simulators in backend/simulators/."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_sim
spec_sim.install(sys.modules[__name__], "production-incident-rootcause", "ROOT_CAUSES")

if __name__ == "__main__":
    spec_sim.cli(sys.modules[__name__])
