"""
Utility functions for muscle3 and torax.
"""

import logging
from typing import Any, Dict, List, Optional, TypeVar, cast, TYPE_CHECKING, overload
import torax

from pydantic import BaseModel
import numpy as np
from imas import IDSFactory
from imas.ids_toplevel import IDSToplevel
from libmuscle import Instance, Grid
from torax._src.geometry.imas import IMASConfig
from ymmsl import Operator

if TYPE_CHECKING:
    from libmuscle.instance import SettingValue
else:
    SettingValue = Any

TSetting = TypeVar("TSetting", bound=SettingValue)

logger = logging.getLogger()


class ExtraVarDir(BaseModel):
    """Temp code for extra vars"""

    name: str
    xs: List[float]
    ys: List


class ExtraVarCollection(BaseModel):
    """Temp code for extra vars"""

    extra_var_dirs: Dict[str, ExtraVarDir] = {}

    @classmethod
    def from_names(cls, names: List[str]) -> "ExtraVarCollection":
        return cls(
            extra_var_dirs={
                name: ExtraVarDir(name=name, xs=[], ys=[]) for name in names
            }
        )

    def add_val(self, name: str, x: float, y: Any) -> None:
        if name not in self.extra_var_dirs.keys():
            self.extra_var_dirs[name] = ExtraVarDir(name=name, xs=[], ys=[])
        self.extra_var_dirs[name].xs.append(x)
        self.extra_var_dirs[name].ys.append(y)

    def pad_extra_vars(self) -> None:
        for name in self.extra_var_dirs.keys():
            self.extra_var_dirs[name].xs = (
                [-np.inf] + self.extra_var_dirs[name].xs + [np.inf]
            )
            self.extra_var_dirs[name].ys = (
                [self.extra_var_dirs[name].ys[0]]
                + self.extra_var_dirs[name].ys
                + [self.extra_var_dirs[name].ys[-1]]
            )

    def get_val(self, name: str, x: float) -> Any:
        """Step interpolation"""
        var_dir = self.extra_var_dirs[name]
        idx = max(i for i in range(len(var_dir.xs)) if var_dir.xs[i] <= x)
        return var_dir.ys[idx]


def get_geometry_config_dict(config: torax.ToraxConfig) -> dict:
    # only get overlapping keys from given config and IMASConfig
    imas_config_keys = IMASConfig.__annotations__
    # we can pick a random entry since all fields are time_invariant except hires_fac
    # (which we can ignore) and equilibrium_object (which we overwrite)
    if isinstance(config.geometry.geometry_configs, dict):
        config_dict = list(config.geometry.geometry_configs.values())[0].config.__dict__
    else:
        config_dict = config.geometry.geometry_configs.config.__dict__
    config_dict = {
        key: value for key, value in config_dict.items() if key in imas_config_keys
    }
    return config_dict


@overload
def get_setting_optional(
    instance: Instance,
    setting_name: str,
    default: None = None,
) -> TSetting | None: ...


@overload
def get_setting_optional(
    instance: Instance,
    setting_name: str,
    default: TSetting,
) -> TSetting: ...


# it may be a nice proposal for the m3 api
def get_setting_optional(
    instance: Instance,
    setting_name: str,
    default: Optional[TSetting] = None,
) -> Optional[TSetting]:
    """Helper function to get optional settings from instance"""
    setting: Optional[TSetting]
    try:
        setting = cast(TSetting, instance.get_setting(setting_name))
    except KeyError:
        setting = default
    return setting


def merge_extra_vars(
    equilibrium_data: IDSToplevel, extra_var_col: ExtraVarCollection
) -> IDSToplevel:
    if "z_boundary_outline" in extra_var_col.extra_var_dirs.keys():
        my_arr = extra_var_col.get_val(
            "z_boundary_outline", equilibrium_data.time[0]
        )
        if isinstance(my_arr, Grid):
            equilibrium_data.time_slice[0].boundary.outline.z = my_arr.array
        else:
            equilibrium_data.time_slice[0].boundary.outline.z = my_arr
    if "r_boundary_outline" in extra_var_col.extra_var_dirs.keys():
        my_arr = extra_var_col.get_val(
            "r_boundary_outline", equilibrium_data.time[0]
        )
        if isinstance(my_arr, Grid):
            equilibrium_data.time_slice[0].boundary.outline.r = my_arr.array
        else:
            equilibrium_data.time_slice[0].boundary.outline.r = my_arr
    return equilibrium_data


def create_light_equilibrium(equilibrium_data: IDSToplevel) -> IDSToplevel:
    """Create a lighter equilibrium IDS  with only the fields needed for geometry.

    Useful to save memory since the full equilibrium can be large if it contains GGD and 2D Profiles.
    It can save a lot of time when processing multiple time slices.
    """
    light_equilibrium = IDSFactory().equilibrium()
    light_equilibrium.ids_properties.homogeneous_time = 1
    light_equilibrium.time = equilibrium_data.time
    light_equilibrium.vacuum_toroidal_field = equilibrium_data.vacuum_toroidal_field
    light_equilibrium.time_slice.resize(len(equilibrium_data.time_slice))
    for i in range(len(light_equilibrium.time_slice)):
        light_equilibrium.time_slice[i].time = equilibrium_data.time_slice[i].time
        light_equilibrium.time_slice[i].profiles_1d = equilibrium_data.time_slice[
            i
        ].profiles_1d
        light_equilibrium.time_slice[i].boundary = equilibrium_data.time_slice[
            i
        ].boundary
        light_equilibrium.time_slice[i].global_quantities = equilibrium_data.time_slice[
            i
        ].global_quantities
    return light_equilibrium


def get_port_list(instance: Instance, operator: Operator) -> List[str]:
    """Filter list of ids_names by which ones are actually connected for
    given instance"""
    total_port_list = instance.list_ports().get(operator, [])
    port_list = [port for port in total_port_list if instance.is_connected(port)]
    return port_list
