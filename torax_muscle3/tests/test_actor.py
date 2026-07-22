import sys
from pathlib import Path
from typing import Any, Dict

import imas
import pytest
import yaml
from imas.ids_defs import CLOSEST_INTERP
from imas.ids_toplevel import IDSToplevel
from libmuscle import Message
from libmuscle.pytest import MuscleTester

import torax_muscle3

TESTS_DIR = Path(torax_muscle3.__path__[0]) / "tests"
DATA_PATH = TESTS_DIR / "data" / "ITERhybrid_COCOS17_IDS_ddv4.nc"
CONFIG_PATH = TESTS_DIR / "basic_config.py"

# torax free-runs from its own config with no external state, so there is no
# f_init/inner-loop combination to exercise here. Two known-unsupported
# combinations are intentionally not covered by a test:
# - core_profiles as f_init input: the test data file has no core_profiles IDS.
# - equilibrium as inner-loop reply source fed back into f_init: a single
#   equilibrium_output slice is not sufficient to reconstruct an equilibrium
#   f_init input.


def build_config(ports: Dict[str, Any]) -> str:
    """Build a v0.2 yMMSL config for the torax program with only the given ports declared.

    Restricting the declared ports controls exactly which ports
    ``MuscleTester`` wires up to the tester component, since torax's actual
    ``Instance`` always declares all 8 ports regardless of what is connected.
    """
    return yaml.safe_dump(
        {
            "ymmsl_version": "v0.2",
            "programs": {
                "torax": {
                    "ports": ports,
                    "executable": sys.executable,
                    "args": ["-m", "torax_muscle3.torax_actor"],
                }
            },
            "settings": {"torax.python_config_module": str(CONFIG_PATH)},
        }
    )


def load_ids(ids_name: str) -> IDSToplevel:
    """Load an IDS from the shared test data file."""
    with imas.DBEntry(uri=str(DATA_PATH), mode="r") as db:
        return db.get(ids_name=ids_name)


def deserialize(ids_name: str, data: bytes) -> IDSToplevel:
    """Deserialize a MUSCLE3 message payload into an IDS."""
    ids = getattr(imas.IDSFactory(), ids_name)()
    ids.deserialize(data)
    return ids


@pytest.mark.filterwarnings("ignore:.*use of fork():DeprecationWarning")
def test_torax_runs_from_initial_equilibrium(muscle3_tester: MuscleTester) -> None:
    """torax builds its initial state from an externally supplied equilibrium and
    free-runs to completion without further MUSCLE3 exchanges."""
    config = build_config(
        {"f_init": ["equilibrium_f_init"], "o_f": ["equilibrium_o_f", "core_profiles_o_f"]}
    )
    tester = muscle3_tester.start_implementation(config, "torax", default_timeout=120)

    equilibrium_ids = load_ids("equilibrium")
    tester.send("equilibrium_f_init", Message(0.0, data=equilibrium_ids.serialize()))

    final_equilibrium = deserialize("equilibrium", tester.receive("equilibrium_o_f").data)
    final_core_profiles = deserialize("core_profiles", tester.receive("core_profiles_o_f").data)
    assert len(final_equilibrium.time) > 0
    assert len(final_core_profiles.time) > 0


@pytest.mark.filterwarnings("ignore:.*use of fork():DeprecationWarning")
def test_torax_output_equilibrium(muscle3_tester: MuscleTester) -> None:
    """torax runs entirely from its own config (no external f_init input) and
    must still emit a valid equilibrium IDS on o_f."""
    config = build_config({"o_f": ["equilibrium_o_f"]})
    tester = muscle3_tester.start_implementation(config, "torax", default_timeout=120)

    final_equilibrium = deserialize("equilibrium", tester.receive("equilibrium_o_f").data)
    assert len(final_equilibrium.time) > 0


@pytest.mark.filterwarnings("ignore:.*use of fork():DeprecationWarning")
def test_torax_output_core_profiles(muscle3_tester: MuscleTester) -> None:
    """torax runs entirely from its own config (no external f_init input) and
    must still emit a valid core_profiles IDS on o_f."""
    config = build_config({"o_f": ["core_profiles_o_f"]})
    tester = muscle3_tester.start_implementation(config, "torax", default_timeout=120)

    final_core_profiles = deserialize("core_profiles", tester.receive("core_profiles_o_f").data)
    assert len(final_core_profiles.time) > 0


@pytest.mark.filterwarnings("ignore:.*use of fork():DeprecationWarning")
def test_torax_reply_equilibrium(muscle3_tester: MuscleTester) -> None:
    """torax's inner time loop is driven with a real reference equilibrium slice,
    interpolated to whatever time it requests on o_i, for every step."""
    config = build_config(
        {
            "s": ["equilibrium_s"],
            "o_i": ["equilibrium_o_i"],
            "o_f": ["equilibrium_o_f", "core_profiles_o_f"],
        }
    )
    tester = muscle3_tester.start_implementation(config, "torax", default_timeout=120)

    with imas.DBEntry("imas:memory?path=/", "w") as reference_db:
        reference_db.put(load_ids("equilibrium"))

        while True:
            request = tester.receive("equilibrium_o_i")
            reply = reference_db.get_slice(
                ids_name="equilibrium",
                time_requested=request.timestamp,
                interpolation_method=CLOSEST_INTERP,
            )
            tester.send(
                "equilibrium_s",
                Message(
                    request.timestamp,
                    data=reply.serialize(),
                    next_timestamp=request.next_timestamp,
                ),
            )
            if request.next_timestamp is None:
                break

    final_equilibrium = deserialize("equilibrium", tester.receive("equilibrium_o_f").data)
    final_core_profiles = deserialize("core_profiles", tester.receive("core_profiles_o_f").data)
    assert len(final_equilibrium.time) > 0
    assert len(final_core_profiles.time) > 0


@pytest.mark.filterwarnings("ignore:.*use of fork():DeprecationWarning")
def test_torax_inner_core_profiles_roundtrip(muscle3_tester: MuscleTester) -> None:
    """torax's own core_profiles output is echoed straight back through its inner
    time loop unchanged, exercising the serialize/deserialize round trip."""
    config = build_config(
        {
            "s": ["core_profiles_s"],
            "o_i": ["core_profiles_o_i"],
            "o_f": ["equilibrium_o_f", "core_profiles_o_f"],
        }
    )
    tester = muscle3_tester.start_implementation(config, "torax", default_timeout=120)

    while True:
        request = tester.receive("core_profiles_o_i")
        tester.send(
            "core_profiles_s",
            Message(
                request.timestamp, data=request.data, next_timestamp=request.next_timestamp
            ),
        )
        if request.next_timestamp is None:
            break

    final_equilibrium = deserialize("equilibrium", tester.receive("equilibrium_o_f").data)
    final_core_profiles = deserialize("core_profiles", tester.receive("core_profiles_o_f").data)
    assert len(final_equilibrium.time) > 0
    assert len(final_core_profiles.time) > 0