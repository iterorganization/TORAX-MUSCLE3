"""Simplified config using mostly defaults for various simulation components."""

CONFIG = {
    "profile_conditions": {
        "I_p": 15e6,
        "psi_source": "geometry",
    },
    "plasma_composition": {},  # use default plasma composition
    "numerics": {},
    # circular geometry is only for testing and prototyping
    "geometry": {
        "model_name": "chease",
        "geometry_file": "iterhybrid.mat2cols",
        "R_major": 6.2,  # major radius (R) in meters
        "a_minor": 2.0,  # minor radius (a) in meters
        "B_0": 5.3,  # Toroidal magnetic field on axis [T]
    },
    "neoclassical": {
        "bootstrap_current": {},
    },
    "sources": {
        # Current sources (for psi equation)
        "generic_current": {
            "fraction_of_total_current": 0.2,
            "gaussian_width": 0.05,
            "gaussian_location": 0.4,
        },
        # Electron density sources/sink (for the n_e equation).
        "generic_particle": {
            "S_total": 1e22,
            "particle_width": 0.25,
            "deposition_location": 0.0,
        },
        "gas_puff": {"S_total": 1e22, "puff_decay_length": 0.05},
        "pellet": {
            "S_total": 2e22,
            "pellet_width": 0.1,
            "pellet_deposition_location": 0.85,
        },
        # Ion and electron heat sources (for the temp-ion and temp-el eqs).
        "generic_heat": {
            "P_total": 120e6,
            "gaussian_width": 0.25,
            "gaussian_location": 0.0,
            "electron_heat_fraction": 0.66666,
        },
        "fusion": {},
        "ei_exchange": {},
        "ohmic": {},
    },
    "pedestal": {},
    "transport": {
        "core_transport_models": {"prescribed": {"model_name": "prescribed"}},
    },
    "solver": {
        "solver_type": "linear",
    },
    "time_step_calculator": {
        "calculator_type": "chi",
        "t_initial": 0,
        "t_final": 5,
        "allow_backtracking": False,
    },
}
