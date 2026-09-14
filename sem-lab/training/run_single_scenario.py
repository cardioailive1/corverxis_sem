"""
CLI entry point the backend's training-run job calls once per scenario.
Wraps training_loop.py's propose + verify logic behind a simple
observations-in, result-out JSON interface.

Usage:
    python3 run_single_scenario.py '<observations_json>' '<hidden_intervention_json>'
"""
import sys
import json
import random
from training_loop import propose_structure
from simulators.industrial_fault_simulator import verify_proposed_structure

if __name__ == "__main__":
    observations = json.loads(sys.argv[1])
    hidden_intervention = json.loads(sys.argv[2])

    proposal = propose_structure(observations, anthropic_client=None)   # offline heuristic — see training_loop.py for the real-API path
    reward = verify_proposed_structure(proposal, hidden_intervention, random.Random())

    print(json.dumps({"proposed": proposal, "reward": reward}))
