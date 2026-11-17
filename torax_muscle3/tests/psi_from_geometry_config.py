"""basic_config with psi owned by the received equilibrium (fixed time stepping)."""

import copy

from torax_muscle3.tests.basic_config import CONFIG as BASIC_CONFIG

CONFIG = copy.deepcopy(BASIC_CONFIG)
CONFIG["numerics"]["evolve_current"] = False
CONFIG["time_step_calculator"] = {
    **CONFIG["time_step_calculator"],
    "calculator_type": "fixed",
    "dt": 0.1,
}
