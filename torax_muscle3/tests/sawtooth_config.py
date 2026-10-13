"""basic_config with sawteeth triggering every step and fixed time stepping."""

import copy

from torax_muscle3.tests.basic_config import CONFIG as BASIC_CONFIG

CONFIG = copy.deepcopy(BASIC_CONFIG)
CONFIG["mhd"] = {
    "sawtooth": {
        "trigger_model": {
            "model_name": "simple",
            "minimum_radius": 0.05,
            "s_critical": 0.1,
        },
        "redistribution_model": {"model_name": "simple"},
    }
}
CONFIG["time_step_calculator"] = {"calculator_type": "fixed"}
