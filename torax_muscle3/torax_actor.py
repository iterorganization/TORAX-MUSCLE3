"""
MUSCLE3 actor wrapping TORAX.

Configuration can be specified as a path to a config file,
and individual muscle3 config keys will be overwritten on that.

Start without inputs and outputs, and then add a static and
later dynamic equilibrium input.

Last (for sure) compatible torax commit: 4b76ef0566
"""

import logging
from typing import Optional, Tuple, Any, Union
import os
import pathlib
import enum

import numpy as np
from imas import DBEntry, IDSFactory
from imas.ids_defs import CLOSEST_INTERP
from imas.ids_toplevel import IDSToplevel
from libmuscle import Instance, InstanceFlags, Message
from torax import experimental as torax_experimental
from torax import (
    build_torax_config_from_file,
    PostProcessedOutputs,
    SimError,
    ToraxConfig,
)
from torax.experimental import (
    RuntimeParamsProvider,
    get_initial_state_and_post_processed_outputs,
    make_step_fn,
    SimState,
    SimulationStepFn,
)
from torax._src.config.build_runtime_params import (
    get_consistent_runtime_params_and_geometry,
)
from torax._src.geometry import geometry
from torax._src.geometry.imas import IMASConfig
from torax._src.geometry.pydantic_model import GeometryConfig
from torax._src.imas_tools.input.core_sources import sources_from_IMAS
from torax._src.imas_tools.input.core_profiles import profile_conditions_from_IMAS
from torax._src.imas_tools.output.core_profiles import core_profiles_to_IMAS
from torax._src.imas_tools.output.equilibrium import torax_state_to_imas_equilibrium
from torax._src.simulation_app import _write_simulation_output_to_dir
from torax._src.output_tools.output import StateHistory
from ymmsl import Operator
import inspect

from torax_muscle3.utils import (
    ExtraVarCollection,
    get_geometry_config_dict,
    get_setting_optional,
    merge_extra_vars,
    create_light_equilibrium,
    get_port_list,
)

logger = logging.getLogger()


def serialize_equilibrium_objects(
    data: Any, key: Optional[Union[str, float]] = None
) -> Any:
    if key == "equilibrium_object":
        return serialize_equilibrium_objects(data.serialize())
    elif isinstance(data, enum.Enum):
        return data.value
    elif inspect.isgenerator(data):
        return serialize_equilibrium_objects(list(data))
    elif isinstance(data, dict):
        return {
            str(k): serialize_equilibrium_objects(v, key=k) for k, v in data.items()
        }
    elif isinstance(data, list):
        return [serialize_equilibrium_objects(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(serialize_equilibrium_objects(item) for item in data)
    elif isinstance(data, pathlib.PosixPath):
        return str(data)
    return data


def deserialize_equilibrium_objects(
    data: Any, key: Optional[Union[str, float]] = None
) -> Any:
    if key == "equilibrium_object":
        eq = IDSFactory().equilibrium()
        eq.deserialize(data)
        return eq
    elif isinstance(data, dict):
        return {
            float(k) if k.isnumeric() else k: deserialize_equilibrium_objects(v, key=k)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [deserialize_equilibrium_objects(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(deserialize_equilibrium_objects(item) for item in data)
    return data


class ToraxMuscleRunner:
    """Object for running torax simulation"""

    first_run: bool = True
    """Whether this is the first reuse_instance loop"""
    output_all_timeslices: bool = False
    """Whether to combine all timeslices at once in the final output"""
    db_out: DBEntry
    """IMAS DBEntry for gathering the timeslices if output_all_timeslices is True"""
    torax_config: ToraxConfig
    """ToraxConfig object"""
    communication_interval: float
    """Interval for communication through MUSCLE3 ports"""
    step_fn: SimulationStepFn
    """Torax step_function object"""
    geometry_provider: torax_experimental.geometry.StandardGeometryProvider
    """Torax geometry_provider object"""
    runtime_params_provider: RuntimeParamsProvider
    """Torax runtime_params_provider object"""
    sim_state: SimState
    """Torax simulation_state object"""
    post_processed_outputs: PostProcessedOutputs
    """Torax post_processed_outputs object"""
    extra_var_col: ExtraVarCollection
    """Object to save state of IDS variables that cannot be saved in Torax state """
    t_cur: float
    """Time value inside time loop"""
    t_final: float
    """Last time value of simulation"""
    t_next_inner: Optional[float] = None
    """Next expected output timestamp for inner time loop"""
    t_next_outer: Optional[float] = None
    """Next expected final output timestamp for reuse_instance loop"""
    finished: bool = False
    """Whether the run_sim function has been run fully"""
    last_communication: float = -np.inf
    """Last timestamp for which the MUSCLE3 communication was done"""

    def __init__(self) -> None:
        self.get_instance()
        self.extra_var_col = ExtraVarCollection()

    def run_sim(self) -> None:
        """Runs a TORAX simulation using the MUSCLE3 actor"""
        if self.finished:
            raise RuntimeError("Already finished")

        while self.instance.reuse_instance():
            if self.instance.resuming():
                self.run_resume()
            if self.instance.should_init():
                if self.first_run:
                    self.run_prep()
                self.run_f_init()
            while not self.step_fn.is_done(self.t_cur):
                self.run_o_i()
                self.run_s()
                self.run_timestep()
                if self.finished:
                    break
                self.save_snapshot()
            self.run_o_f()
            self.save_final_snapshot()

        self.finished = True

    def run_resume(self) -> None:
        # receive message
        msg = self.instance.load_snapshot()
        # unpack class vars
        self.first_run = msg.data[0]["first_run"]
        self.t_cur = msg.data[0]["t_cur"]
        self.t_final = msg.data[0]["t_final"]
        self.t_next_inner = msg.data[0]["t_next_inner"]
        self.t_next_outer = msg.data[0]["t_next_outer"]
        self.finished = msg.data[0]["finished"]
        self.last_communication = msg.data[0]["last_communication"]
        self.torax_config = ToraxConfig.from_dict(
            deserialize_equilibrium_objects(msg.data[0]["torax_config"])
        )
        # unpack netcdf path, deserialize and add to class vars
        self.torax_config.update_fields(
            {
                "restart": {
                    "filename": msg.data[0]["netcdf_path"],
                    "time": self.t_cur,
                    "do_restart": True,
                    "stitch": True,
                }
            }
        )
        # run_prep with given torax_config (add optional arg)
        self.run_prep(self.torax_config)
        self.extra_var_col = ExtraVarCollection.model_validate(
            msg.data[0]["extra_var_col"]
        )
        if self.output_all_timeslices:
            self.db_out = DBEntry("imas:memory?path=/db_out/", "w")
            for ids_name, obj in msg.data[0]["db_out"].items():
                ids = self.db_out.factory.new(ids_name)
                ids.deserialize(obj)
                self.db_out.put(ids)
        self.sim_state, self.post_processed_outputs = (
            get_initial_state_and_post_processed_outputs(
                step_fn=self.step_fn,
                geometry_overrides=self.geometry_provider,
                runtime_params_overrides=self.runtime_params_provider,
            )
        )

    def save_snapshot(self) -> None:
        if self.instance.should_save_snapshot(self.t_cur):
            # store class vars
            # save sim_state and state history to netcdf, store path
            sim_error = self.step_fn.check_for_errors(
                self.sim_state,
                self.post_processed_outputs,
            )
            config_module_str = self.instance.get_setting("python_config_module")
            my_torax_config = build_torax_config_from_file(
                path=config_module_str,
            )
            data_tree = StateHistory(
                state_history=[self.sim_state],
                post_processed_outputs_history=[self.post_processed_outputs],
                sim_error=sim_error,
                # torax_config=self.torax_config,
                torax_config=my_torax_config,
            ).simulation_output_to_xr()
            output_dir = "blabla"
            output_file = _write_simulation_output_to_dir(output_dir, data_tree)
            output_file = os.path.abspath(output_file)
            # store current torax_config
            # send message
            my_torax_config = serialize_equilibrium_objects(
                self.torax_config.model_dump()
            )
            data = [
                {
                    "first_run": bool(self.first_run),
                    "t_cur": float(self.t_cur),
                    "t_final": float(self.t_final),
                    "t_next_inner": float(self.t_next_inner)
                    if self.t_next_inner is not None
                    else None,
                    "t_next_outer": float(self.t_next_outer)
                    if self.t_next_outer is not None
                    else None,
                    "finished": self.finished,
                    "last_communication": float(self.last_communication)
                    if self.last_communication is not None
                    else None,
                    "netcdf_path": output_file,
                    "torax_config": my_torax_config,
                    "extra_var_col": self.extra_var_col.model_dump(),
                    "db_out": {
                        ids_name: self.db_out.get(ids_name).serialize()
                        for ids_name in [
                            port.replace("_o_f", "")
                            for port in get_port_list(self.instance, Operator.O_F)
                        ]
                    },
                }
            ]
            msg = Message(float(self.t_cur), data=data)
            self.instance.save_snapshot(msg)

    def save_final_snapshot(self) -> None:
        if self.instance.should_save_final_snapshot():
            msg = Message(float(self.t_cur))
            self.instance.save_final_snapshot(msg)

    def run_prep(self, torax_config: Optional[ToraxConfig] = None) -> None:
        """Prepare a TORAX simulation based on torax config and MUSCLE3 settings"""
        self.communication_interval = get_setting_optional(
            self.instance, "communication_interval", 1e-6
        )
        self.output_all_timeslices = get_setting_optional(
            self.instance, "output_all_timeslices", False
        )
        if self.output_all_timeslices:
            self.db_out = DBEntry("imas:memory?path=/db_out/", "w")
        if torax_config is None:
            # load config file from path
            config_module_str = self.instance.get_setting("python_config_module")
            self.torax_config = build_torax_config_from_file(
                path=config_module_str,
            )
        else:
            self.torax_config = torax_config
        self.fix_ymmsl_settings()
        self.geometry_provider = self.torax_config.geometry.build_provider
        self.runtime_params_provider = RuntimeParamsProvider.from_config(
            self.torax_config
        )
        self.step_fn = make_step_fn(self.torax_config)

    def run_f_init(self) -> None:
        """Initialize the actor state before the time loop using MUSCLE3 connections"""
        self.receive_equilibrium(port_name="f_init")
        self.receive_core_profiles(port_name="f_init")
        self.receive_core_sources(port_name="f_init")
        if self.first_run or self.instance.is_connected("equilibrium_f_init"):
            self.step_fn = make_step_fn(self.torax_config)
            self.sim_state, self.post_processed_outputs = (
                get_initial_state_and_post_processed_outputs(
                    step_fn=self.step_fn,
                    geometry_overrides=self.geometry_provider,
                    runtime_params_overrides=self.runtime_params_provider,
                )
            )
            self.t_final = self.step_fn.runtime_params_provider.numerics.t_final
        self.t_cur = self.sim_state.t
        self.first_run = False

        if self.output_all_timeslices:
            self.db_out.put_slice(self.get_equilibrium_ids())
            self.db_out.put_slice(self.get_core_profiles_ids())

    def run_o_i(self) -> None:
        """Send out time loop state using MUSCLE3 connections"""
        self.t_next_inner = self.get_t_next()
        if self.t_cur >= self.last_communication + self.communication_interval:
            self.last_communication = self.t_cur
            if self.instance.is_connected("equilibrium_o_i"):
                self.send_ids(self.get_equilibrium_ids(), "equilibrium", "o_i")
            if self.instance.is_connected("core_profiles_o_i"):
                self.send_ids(self.get_core_profiles_ids(), "core_profiles", "o_i")

    def run_s(self) -> None:
        """Update time loop state using MUSCLE3 connections"""
        if self.t_cur >= self.last_communication + self.communication_interval:
            self.receive_equilibrium(port_name="s")
            self.receive_core_profiles(port_name="s")
            self.receive_core_sources(port_name="s")

    def run_timestep(self) -> None:
        """Evolve time loop state using the TORAX step function"""
        self.sim_state, self.post_processed_outputs = self.step_fn(
            self.sim_state,
            self.post_processed_outputs,
            geo_overrides=self.geometry_provider,
            runtime_params_overrides=self.runtime_params_provider,
        )
        sim_error = self.step_fn.check_for_errors(
            self.sim_state,
            self.post_processed_outputs,
        )
        self.t_cur = self.sim_state.t

        if sim_error != SimError.NO_ERROR:
            self.finished = True
            return

        if self.output_all_timeslices:
            if self.t_cur >= self.last_communication + self.communication_interval:
                self.db_out.put_slice(self.get_equilibrium_ids())
                self.db_out.put_slice(self.get_core_profiles_ids())

    def run_o_f(self) -> None:
        """Send out final state using MUSCLE3 connections"""
        if self.output_all_timeslices:
            equilibrium_data = self.db_out.get("equilibrium")
            core_profiles_data = self.db_out.get("core_profiles")
            self.db_out.close()
        else:
            equilibrium_data = self.get_equilibrium_ids()
            core_profiles_data = self.get_core_profiles_ids()
        self.send_ids(equilibrium_data, "equilibrium", "o_f")
        self.send_ids(core_profiles_data, "core_profiles", "o_f")

    def get_instance(self) -> None:
        """Initialize MUSCLE3 instance and set up connection ports"""
        coupled_ids_names = ["equilibrium", "core_profiles", "core_sources"]
        self.instance = Instance(
            {
                Operator.F_INIT: [
                    f"{ids_name}_f_init" for ids_name in coupled_ids_names
                ],
                Operator.O_I: [f"{ids_name}_o_i" for ids_name in coupled_ids_names],
                Operator.S: [f"{ids_name}_s" for ids_name in coupled_ids_names],
                Operator.O_F: [f"{ids_name}_o_f" for ids_name in coupled_ids_names],
            },
            flags=InstanceFlags.USES_CHECKPOINT_API,
        )

    def get_equilibrium_ids(self) -> IDSToplevel:
        """Get equilibrium IDS from torax state"""
        equilibrium_data = torax_state_to_imas_equilibrium(
            self.sim_state, self.post_processed_outputs
        )
        if self.extra_var_col is not None:
            equilibrium_data = merge_extra_vars(equilibrium_data, self.extra_var_col)
        return equilibrium_data

    def get_core_profiles_ids(self) -> IDSToplevel:
        """Get core_profiles IDS from torax state"""
        core_profiles_data = core_profiles_to_IMAS(
            self.torax_config,
            [self.post_processed_outputs],
            [self.sim_state.core_profiles],
            [self.sim_state.core_sources],
            [self.sim_state.geometry],
            [self.sim_state.t],
        )
        return core_profiles_data

    def receive_equilibrium(self, port_name: str) -> None:
        """Receive equilibrium IDS through MUSCLE3 connections"""
        if not self.instance.is_connected(f"equilibrium_{port_name}"):
            return
        equilibrium_data, self.t_cur, t_next = self.receive_ids_data(
            "equilibrium", port_name
        )
        self.update_t_next(t_next, port_name)

        # if output_flag is -1 it means the code did not run successfully
        # and the result should not be used
        if (
            equilibrium_data.code.output_flag
            and equilibrium_data.code.output_flag[0] == -1
        ):
            return

        geometry_configs = {}
        torax_config_dict = get_geometry_config_dict(self.torax_config)
        torax_config_dict["geometry_type"] = "imas"
        light_equilibrium = create_light_equilibrium(equilibrium_data)
        with DBEntry("imas:memory?path=/", "w") as db:
            db.put(light_equilibrium)
            for t in light_equilibrium.time:
                my_slice = db.get_slice(
                    ids_name="equilibrium",
                    time_requested=t,
                    interpolation_method=CLOSEST_INTERP,
                )
                if my_slice.code.output_flag and my_slice.code.output_flag[0] == -1:
                    continue
                config_kwargs = {
                    **torax_config_dict,
                    "equilibrium_object": my_slice,
                    "imas_uri": None,
                    "imas_filepath": None,
                    "Ip_from_parameters": False,
                }
                imas_cfg = IMASConfig(**config_kwargs)
                cfg = GeometryConfig(config=imas_cfg)
                geometry_configs[str(t)] = cfg
                # temp extra vars code
                self.extra_var_col.add_val(
                    "z_boundary_outline",
                    t,
                    np.asarray(my_slice.time_slice[0].boundary.outline.z),
                )
                self.extra_var_col.add_val(
                    "r_boundary_outline",
                    t,
                    np.asarray(my_slice.time_slice[0].boundary.outline.r),
                )
        # temp extra vars code
        self.extra_var_col.pad_extra_vars()

        # self.geometry_provider = torax_experimental.geometry.Geometry.from_dict(
        #     {
        #         "geometry_type": geometry.GeometryType.IMAS,
        #         "geometry_configs": geometry_configs,
        #     }
        # ).build_provider

        self.torax_config.update_fields(
            {
                "geometry": {
                    "geometry_type": geometry.GeometryType.IMAS,
                    "geometry_configs": geometry_configs,
                }
            }
        )
        self.geometry_provider = self.torax_config.geometry.build_provider

    def receive_core_profiles(self, port_name: str) -> None:
        """Receive core_profiles IDS through MUSCLE3 connections"""
        if not self.instance.is_connected(f"core_profiles_{port_name}"):
            return
        core_profiles_data, self.t_cur, t_next = self.receive_ids_data(
            "core_profiles", port_name
        )
        self.update_t_next(t_next, port_name)

        # ignore this entry if input source didn't converge
        if (
            core_profiles_data.code.output_flag
            and core_profiles_data.code.output_flag[0] == -1
        ):
            return
        core_profiles_conditions = profile_conditions_from_IMAS(core_profiles_data)
        self.torax_config.update_fields(
            {"profile_conditions": core_profiles_conditions}
        )
        self.runtime_params_provider = RuntimeParamsProvider.from_config(
            self.torax_config
        )

    def receive_core_sources(self, port_name: str) -> None:
        """Receive core_sources IDS through MUSCLE3 connections"""
        if not self.instance.is_connected(f"core_sources_{port_name}"):
            return
        core_sources_data, self.t_cur, t_next = self.receive_ids_data(
            "core_sources", port_name
        )
        self.update_t_next(t_next, port_name)

        # ignore this entry if input source didn't converge
        if (
            core_sources_data.code.output_flag
            and core_sources_data.code.output_flag[0] == -1
        ):
            return

        sources = sources_from_IMAS(core_sources_data)
        self.torax_config.update_fields(
            {f"sources.{key}": value for key, value in sources.items()}
        )
        self.runtime_params_provider = RuntimeParamsProvider.from_config(
            self.torax_config
        )

    def receive_ids_data(
        self, ids_name: str, port_name: str
    ) -> Tuple[IDSToplevel, float, Optional[float]]:
        """Receive IDS message through MUSCLE3"""
        if not self.instance.is_connected(f"{ids_name}_{port_name}"):
            raise Warning("Calling receive while not connected")
        msg = self.instance.receive(f"{ids_name}_{port_name}")
        t_cur = msg.timestamp
        t_next = msg.next_timestamp
        ids_data = getattr(IDSFactory(), ids_name)()
        ids_data.deserialize(msg.data)
        return ids_data, t_cur, t_next

    def send_ids(self, ids: IDSToplevel, ids_name: str, port_name: str) -> None:
        """Send IDS message through MUSCLE3"""
        if not self.instance.is_connected(f"{ids_name}_{port_name}"):
            return
        if port_name == "o_i":
            t_next = self.t_next_inner
        elif port_name == "o_f":
            t_next = self.t_next_outer
        msg = Message(self.t_cur, data=ids.serialize(), next_timestamp=t_next)
        self.instance.send(f"{ids_name}_{port_name}", msg)

    def get_t_next(self) -> Optional[float]:
        """Calculate expected next timestamp in time loop"""
        runtime_params_t, geo_t = get_consistent_runtime_params_and_geometry(
            t=self.sim_state.t,
            runtime_params_provider=self.runtime_params_provider,
            geometry_provider=self.geometry_provider,
            core_profiles=self.sim_state.core_profiles,
        )
        dt = self.step_fn.time_step_calculator.next_dt(
            runtime_params_t,
            self.sim_state,
        )
        t_next = self.sim_state.t + dt
        if t_next >= self.t_final:
            t_next = None
        return t_next

    def update_t_next(self, t_next: Optional[float], port_name: str) -> None:
        """Update t_next to given value"""
        if port_name == "f_init":
            self.t_next_outer = t_next
        elif port_name == "s":
            self.t_next_inner = t_next

    def fix_ymmsl_settings(self) -> None:
        for numerics_setting in [
            "t_initial",
            "t_final",
            "fixed_dt",
        ]:
            var = get_setting_optional(self.instance, numerics_setting, None)
            if var is not None:
                self.torax_config.update_fields({f"numerics.{numerics_setting}": var})


def main() -> None:
    """Create TORAX instance and enter submodel execution loop"""
    logger.info("Starting TORAX actor")
    tmr = ToraxMuscleRunner()
    tmr.run_sim()


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    main()
