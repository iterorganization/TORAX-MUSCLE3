import sys
from pathlib import Path
from typing import Any, Dict, Optional

import imas
import libmuscle
import pytest
import yaml
import ymmsl
from imas.ids_defs import CLOSEST_INTERP
from imas.ids_toplevel import IDSToplevel
from libmuscle import Message
from libmuscle.pytest import MuscleTester

import torax_muscle3
from torax_muscle3.torax_actor import main as torax_actor
from torax_muscle3.torax_actor import numerics_overrides

TESTS_DIR = Path(torax_muscle3.__path__[0]) / "tests"
EQUILIBRIUM_DATA_PATH = TESTS_DIR / "data" / "ITERhybrid_COCOS17_IDS_ddv4.nc"
CORE_SOURCES_DATA_PATH = TESTS_DIR / "data" / "core_sources_ddv4.nc"
CONFIG_PATH = TESTS_DIR / "basic_config.py"

# ---------------------------------------------------------------------------
# MuscleTester-based tests: drive the real torax actor directly through the
# MUSCLE3 pytest testing framework
# (https://muscle3.readthedocs.io/en/latest/muscle_tester.html), instead of
# through hand-rolled mock actors + libmuscle.runner.run_simulation.
#
# Two known-unsupported combinations are intentionally not covered by a test:
# - core_profiles as f_init input: the test data file has no core_profiles IDS.
# - equilibrium as inner-loop reply source fed back into f_init: a single
#   equilibrium_output slice is not sufficient to reconstruct an equilibrium
#   f_init input.
# ---------------------------------------------------------------------------


def build_config(ports: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> str:
    """Build a v0.2 yMMSL config for the torax program with only the given ports declared.

    Restricting the declared ports controls exactly which ports
    ``MuscleTester`` wires up to the tester component, since torax's actual
    ``Instance`` always declares all 12 ports regardless of what is connected.
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
            "settings": {
                "torax.python_config_module": str(CONFIG_PATH),
                **(settings or {}),
            },
        }
    )


def load_ids(data_path: Path, ids_name: str) -> IDSToplevel:
    """Load an IDS from a test data file."""
    with imas.DBEntry(uri=str(data_path), mode="r") as db:
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
        {"f_init": ["equilibrium_in_f"], "o_f": ["equilibrium_out_f", "core_profiles_out_f"]},
        # The test equilibrium has a single time point, which would otherwise
        # collapse torax's auto-derived simulation window to zero length.
        settings={"torax.t_initial": 0, "torax.t_final": 5},
    )
    tester = muscle3_tester.start_implementation(config, "torax", default_timeout=120)

    equilibrium_ids = load_ids(EQUILIBRIUM_DATA_PATH, "equilibrium")
    tester.send("equilibrium_in_f", Message(0.0, data=equilibrium_ids.serialize()))

    final_equilibrium = deserialize("equilibrium", tester.receive("equilibrium_out_f").data)
    final_core_profiles = deserialize("core_profiles", tester.receive("core_profiles_out_f").data)
    assert len(final_equilibrium.time) > 0
    assert len(final_core_profiles.time) > 0


@pytest.mark.filterwarnings("ignore:.*use of fork():DeprecationWarning")
def test_torax_input_core_sources(muscle3_tester: MuscleTester) -> None:
    """torax applies externally supplied core_sources at f_init and free-runs to
    completion using its own config for everything else."""
    config = build_config(
        {"f_init": ["core_sources_in_f"], "o_f": ["equilibrium_out_f", "core_profiles_out_f"]}
    )
    tester = muscle3_tester.start_implementation(config, "torax", default_timeout=120)

    core_sources_ids = load_ids(CORE_SOURCES_DATA_PATH, "core_sources")
    tester.send("core_sources_in_f", Message(0.0, data=core_sources_ids.serialize()))

    final_equilibrium = deserialize("equilibrium", tester.receive("equilibrium_out_f").data)
    final_core_profiles = deserialize("core_profiles", tester.receive("core_profiles_out_f").data)
    assert len(final_equilibrium.time) > 0
    assert len(final_core_profiles.time) > 0


@pytest.mark.filterwarnings("ignore:.*use of fork():DeprecationWarning")
def test_torax_output_equilibrium(muscle3_tester: MuscleTester) -> None:
    """torax runs entirely from its own config (no external f_init input) and
    must still emit a valid equilibrium IDS on o_f."""
    config = build_config({"o_f": ["equilibrium_out_f"]})
    tester = muscle3_tester.start_implementation(config, "torax", default_timeout=120)

    final_equilibrium = deserialize("equilibrium", tester.receive("equilibrium_out_f").data)
    assert len(final_equilibrium.time) > 0


@pytest.mark.filterwarnings("ignore:.*use of fork():DeprecationWarning")
def test_torax_output_core_profiles(muscle3_tester: MuscleTester) -> None:
    """torax runs entirely from its own config (no external f_init input) and
    must still emit a valid core_profiles IDS on o_f."""
    config = build_config({"o_f": ["core_profiles_out_f"]})
    tester = muscle3_tester.start_implementation(config, "torax", default_timeout=120)

    final_core_profiles = deserialize("core_profiles", tester.receive("core_profiles_out_f").data)
    assert len(final_core_profiles.time) > 0


@pytest.mark.filterwarnings("ignore:.*use of fork():DeprecationWarning")
def test_torax_reply_equilibrium(muscle3_tester: MuscleTester) -> None:
    """torax's inner time loop is driven with a real reference equilibrium slice,
    interpolated to whatever time it requests on o_i, for every step."""
    config = build_config(
        {
            "s": ["equilibrium_in_s"],
            "o_i": ["equilibrium_out_i"],
            "o_f": ["equilibrium_out_f", "core_profiles_out_f"],
        }
    )
    tester = muscle3_tester.start_implementation(config, "torax", default_timeout=120)

    with imas.DBEntry("imas:memory?path=/", "w") as reference_db:
        reference_db.put(load_ids(EQUILIBRIUM_DATA_PATH, "equilibrium"))

        while True:
            request = tester.receive("equilibrium_out_i")
            reply = reference_db.get_slice(
                ids_name="equilibrium",
                time_requested=request.timestamp,
                interpolation_method=CLOSEST_INTERP,
            )
            tester.send(
                "equilibrium_in_s",
                Message(
                    request.timestamp,
                    data=reply.serialize(),
                    next_timestamp=request.next_timestamp,
                ),
            )
            if request.next_timestamp is None:
                break

    final_equilibrium = deserialize("equilibrium", tester.receive("equilibrium_out_f").data)
    final_core_profiles = deserialize("core_profiles", tester.receive("core_profiles_out_f").data)
    assert len(final_equilibrium.time) > 0
    assert len(final_core_profiles.time) > 0


@pytest.mark.filterwarnings("ignore:.*use of fork():DeprecationWarning")
def test_torax_inner_core_profiles_roundtrip(muscle3_tester: MuscleTester) -> None:
    """torax's own core_profiles output is echoed straight back through its inner
    time loop unchanged, exercising the serialize/deserialize round trip."""
    config = build_config(
        {
            "s": ["core_profiles_in_s"],
            "o_i": ["core_profiles_out_i"],
            "o_f": ["equilibrium_out_f", "core_profiles_out_f"],
        }
    )
    tester = muscle3_tester.start_implementation(config, "torax", default_timeout=120)

    while True:
        request = tester.receive("core_profiles_out_i")
        tester.send(
            "core_profiles_in_s",
            Message(
                request.timestamp, data=request.data, next_timestamp=request.next_timestamp
            ),
        )
        if request.next_timestamp is None:
            break

    final_equilibrium = deserialize("equilibrium", tester.receive("equilibrium_out_f").data)
    final_core_profiles = deserialize("core_profiles", tester.receive("core_profiles_out_f").data)
    assert len(final_equilibrium.time) > 0
    assert len(final_core_profiles.time) > 0


# ---------------------------------------------------------------------------
# Checkpoint/resume test: exercises MUSCLE3's snapshot/resume mechanics across
# two separate manager runs. MuscleTester/ImplementationTester has no
# snapshot/resume controls (it drives a single implementation interactively),
# so this keeps the old mock-actor + libmuscle.runner.run_simulation approach.
# ---------------------------------------------------------------------------


def source_for_tests():
    """MUSCLE3 actor sending out imas data to test torax-muscle3 actor"""
    instance = libmuscle.Instance(flags=libmuscle.InstanceFlags.USES_CHECKPOINT_API)
    ports = instance.list_ports()[ymmsl.Operator.O_F]
    imas_filepath = instance.get_setting("imas_source")
    with imas.DBEntry(uri=imas_filepath, mode="r") as db:
        while instance.reuse_instance():
            if instance.resuming():
                pass
            if instance.should_init():
                pass
            for port in ports:
                ids_name = port.replace("_out", "")
                ids_data = db.get(ids_name=ids_name)
                msg_out = libmuscle.Message(
                    0, data=ids_data.serialize(), next_timestamp=None
                )
                instance.send(port, msg_out)
            if instance.should_save_final_snapshot():
                msg = libmuscle.Message(0)
                instance.save_final_snapshot(msg)


def sink_for_tests():
    """MUSCLE3 actor receiving imas data to test torax-muscle3 actor"""
    instance = libmuscle.Instance(flags=libmuscle.InstanceFlags.USES_CHECKPOINT_API)
    ports = instance.list_ports()[ymmsl.Operator.F_INIT]
    data_sink_path = instance.get_setting("imas_sink")
    with imas.DBEntry(uri=data_sink_path, mode="w") as db:
        while instance.reuse_instance():
            if instance.resuming():
                pass
            if instance.should_init():
                pass
            for port in ports:
                ids_name = port.replace("_in", "")
                msg_in = instance.receive(port)
                ids_data = getattr(imas.IDSFactory(), ids_name)()
                ids_data.deserialize(msg_in.data)
                db.put(ids_data)
            if instance.should_save_final_snapshot():
                msg = libmuscle.Message(0)
                instance.save_final_snapshot(msg)


YMMSL_CHECKPOINT_TEMPLATE = """
ymmsl_version: v0.1
model:
  name: test_model
  components:
    source:
      implementation: source
      ports:
        o_f: [IDS_NAME_out]
    sink:
      implementation: sink
      ports:
        f_init: [IDS_NAME_in]
    torax:
      implementation: torax
      ports:
        f_init: [IDS_NAME_in_f]
        o_f: [IDS_NAME_out_f]
  conduits:
    source.IDS_NAME_out: torax.IDS_NAME_in_f
    torax.IDS_NAME_out_f: sink.IDS_NAME_in
settings:
  source.imas_source: {data_source_path}
  sink.imas_sink: {data_sink_path}
  torax.python_config_module: {config_path}
checkpoints:
  at_end: true
  simulation_time:
  - every: 100
"""

YMMSL_RESUME_TEMPLATE = (
    YMMSL_CHECKPOINT_TEMPLATE
    + """
\n
resume:
  source: {workdir}/source_1.pack
  sink: {workdir}/sink_1.pack
  torax: {workdir}/torax_1.pack
"""
)

YMMSL_CHECKPOINT_EQUILIBRIUM = YMMSL_CHECKPOINT_TEMPLATE.replace(
    "IDS_NAME", "equilibrium"
)
YMMSL_RESUME_EQUILIBRIUM = YMMSL_RESUME_TEMPLATE.replace("IDS_NAME", "equilibrium")


@pytest.mark.parametrize(
    "ymmsl_text, ymmsl_resume",
    [
        pytest.param(
            YMMSL_CHECKPOINT_EQUILIBRIUM,
            YMMSL_RESUME_EQUILIBRIUM,
            id="checkpoint equilibrium",
        ),
    ],
)
@pytest.mark.filterwarnings("ignore:.*use of fork():DeprecationWarning")
def test_checkpoint(tmp_path, monkeypatch, ymmsl_text, ymmsl_resume):
    monkeypatch.chdir(tmp_path)

    filename = "ITERhybrid_COCOS17_IDS_ddv4.nc"
    data_source_path = f"{torax_muscle3.__path__[0]}/tests/data/{filename}"
    data_sink_path = f"imas:hdf5?path={(tmp_path / 'sink_dir').absolute()}"
    config_path = f"{torax_muscle3.__path__[0]}/tests/basic_config.py"
    implementations = {
        "sink": sink_for_tests,
        "source": source_for_tests,
        "torax": torax_actor,
    }

    configuration = ymmsl.load(
        ymmsl_text.format(
            data_source_path=data_source_path,
            data_sink_path=data_sink_path,
            config_path=config_path,
        )
    )
    libmuscle.runner.run_simulation(configuration, implementations)

    configuration = ymmsl.load(
        ymmsl_resume.format(
            data_source_path=data_source_path,
            data_sink_path=data_sink_path,
            config_path=config_path,
            workdir=tmp_path,
        )
    )
    libmuscle.runner.run_simulation(configuration, implementations)


# ---------------------------------------------------------------------------
# Pure unit tests for the numerics-window precedence logic.
# ---------------------------------------------------------------------------

NO_YMMSL_NUMERICS = {"t_initial": None, "t_final": None, "fixed_dt": None}


def test_time_window_from_equilibrium():
    """t_range from the received equilibrium sequence sets the window."""
    assert numerics_overrides((1.5, 3.25), NO_YMMSL_NUMERICS) == {
        "numerics.t_initial": 1.5,
        "numerics.t_final": 3.25,
    }


def test_ymmsl_numerics_override_equilibrium_window():
    """Explicit ymmsl t_initial/t_final win over the equilibrium-derived range."""
    assert numerics_overrides(
        (1.5, 3.25), {"t_initial": 2.0, "t_final": 4.0, "fixed_dt": None}
    ) == {"numerics.t_initial": 2.0, "numerics.t_final": 4.0}


def test_partial_ymmsl_keeps_equilibrium_window():
    """A ymmsl override of only fixed_dt leaves the equilibrium window intact."""
    assert numerics_overrides(
        (1.5, 3.25), {"t_initial": None, "t_final": None, "fixed_dt": 0.05}
    ) == {
        "numerics.t_initial": 1.5,
        "numerics.t_final": 3.25,
        "numerics.fixed_dt": 0.05,
    }