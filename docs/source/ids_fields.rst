.. _`ids_fields`:

IDS Inputs and Outputs
######################

For more information on the IMAS Data Dictionary and IDS data structures, see the `IDS reference documentation <https://sharepoint.iter.org/departments/POP/CM/IMDesign/Data%20Model/sphinx/4.0/reference_ids.html>`_.

This page shows the required inputs and outputs per IDS for the TORAX-MUSCLE3 actor

Required inputs
---------------

Equilibrium
^^^^^^^^^^^

- ids.time
- ids.vacuum_toroidal_field.r0
- ids.vacuum_toroidal_field.b0
- ids.time_slice[].profiles_1d.psi
- ids.time_slice[].profiles_1d.phi
- ids.time_slice[].profiles_1d.r_inboard
- ids.time_slice[].profiles_1d.r_outboard
- ids.time_slice[].profiles_1d.f
- ids.time_slice[].profiles_1d.dvolume_dpsi
- ids.time_slice[].profiles_1d.volume
- ids.time_slice[].profiles_1d.dpsi_drho_tor
- ids.time_slice[].profiles_1d.rho_tor
- ids.time_slice[].profiles_1d.gm1
- ids.time_slice[].profiles_1d.gm2
- ids.time_slice[].profiles_1d.gm3
- ids.time_slice[].profiles_1d.gm4
- ids.time_slice[].profiles_1d.gm5
- ids.time_slice[].profiles_1d.gm7
- ids.time_slice[].profiles_1d.gm9
- ids.time_slice[].profiles_1d.j_phi
- ids.time_slice[].profiles_1d.rho_tor_norm
- ids.time_slice[].profiles_1d.triangularity_upper
- ids.time_slice[].profiles_1d.triangularity_lower
- ids.time_slice[].profiles_1d.elongation
- ids.time_slice[].global_quantities.ip
- ids.time_slice[].global_quantities.magnetic_axis.z
- ids.time_slice[].boundary.minor_radius
- ids.time_slice[].boundary.type

Core profiles
^^^^^^^^^^^^^

- ids.time
- ids.global_quantities.ip
- ids.global_quantities.v_loop
- ids.time_slice[].profiles_1d.grid.psi
- ids.time_slice[].profiles_1d.electrons.temperature
- ids.time_slice[].profiles_1d.electrons.density
- ids.time_slice[].profiles_1d.t_i_average
- ids.time_slice[].profiles_1d.ion[].temperature
- ids.time_slice[].profiles_1d.ion[].density

Outputs
-------

Equilibrium
^^^^^^^^^^^

- ids.ids_properties.homogeneous_time
- ids.ids_properties.comment
- ids.time
- ids.vacuum_toroidal_field.r0
- ids.vacuum_toroidal_field.b0
- ids.time_slice[].boundary.geometric_axis.r
- ids.time_slice[].boundary.minor_radius
- ids.time_slice[].boundary.outline.r (optional)
- ids.time_slice[].boundary.outline.z (optional)
- ids.time_slice[].global_quantities.magnetic_axis.z
- ids.time_slice[].global_quantities.ip
- ids.time_slice[].profiles_1d.psi
- ids.time_slice[].profiles_1d.phi
- ids.time_slice[].profiles_1d.r_inboard
- ids.time_slice[].profiles_1d.r_outboard
- ids.time_slice[].profiles_1d.triangularity_lower
- ids.time_slice[].profiles_1d.triangularity_upper
- ids.time_slice[].profiles_1d.elongation
- ids.time_slice[].profiles_1d.j_phi
- ids.time_slice[].profiles_1d.volume
- ids.time_slice[].profiles_1d.area
- ids.time_slice[].profiles_1d.rho_tor
- ids.time_slice[].profiles_1d.rho_tor_norm
- ids.time_slice[].profiles_1d.dpsi_drho_tor
- ids.time_slice[].profiles_1d.dvolume_dpsi
- ids.time_slice[].profiles_1d.gm1
- ids.time_slice[].profiles_1d.gm2
- ids.time_slice[].profiles_1d.gm3
- ids.time_slice[].profiles_1d.gm7
- ids.time_slice[].profiles_1d.pressure
- ids.time_slice[].profiles_1d.dpressure_dpsi
- ids.time_slice[].profiles_1d.f
- ids.time_slice[].profiles_1d.f_df_dpsi
- ids.time_slice[].profiles_1d.q

Core profiles
^^^^^^^^^^^^^

- ids.ids_properties.comment
- ids.ids_properties.homogeneous_time
- ids.ids_properties.creation_date
- ids.code.name
- ids.code.description
- ids.code.repository
- ids.time
- ids.vacuum_toroidal_field.r0
- ids.vacuum_toroidal_field.b0
- ids.global_quantities.ip
- ids.global_quantities.current_bootstrap
- ids.global_quantities.v_loop
- ids.global_quantities.li_3
- ids.global_quantities.beta_pol
- ids.global_quantities.beta_tor
- ids.global_quantities.beta_tor_norm
- ids.global_quantities.t_e_volume_average
- ids.global_quantities.n_e_volume_average
- ids.global_quantities.ion_time_slice
- ids.global_quantities.ion[].t_i_volume_average
- ids.global_quantities.ion[].n_i_volume_average
- ids.profiles_1d.time
- ids.profiles_1d.t_i_average
- ids.profiles_1d.n_i_total_over_n_e
- ids.profiles_1d.pressure_thermal
- ids.profiles_1d.zeff
- ids.profiles_1d.electrons.temperature
- ids.profiles_1d.electrons.density
- ids.profiles_1d.electrons.density_thermal
- ids.profiles_1d.electrons.density_fast
- ids.profiles_1d.electrons.pressure_thermal
- ids.profiles_1d.electrons.pressure_ion_total
- ids.profiles_1d.ion.name
- ids.profiles_1d.ion.label
- ids.profiles_1d.ion.temperature
- ids.profiles_1d.ion.density
- ids.profiles_1d.ion.density_thermal
- ids.profiles_1d.ion.density_fast
- ids.profiles_1d.ion.element.a
- ids.profiles_1d.ion.element.z_n
- ids.profiles_1d.ion.t_i_volume_average
- ids.profiles_1d.ion.n_i_volume_average
- ids.profiles_1d.grid.rho_tor_norm
- ids.profiles_1d.grid.rho_tor
- ids.profiles_1d.grid.psi
- ids.profiles_1d.grid.psi_magnetic_axis
- ids.profiles_1d.grid.psi_boundary
- ids.profiles_1d.grid.rho_pol_norm
- ids.profiles_1d.grid.volume
- ids.profiles_1d.grid.area
- ids.profiles_1d.q
- ids.profiles_1d.magnetic_shear
- ids.profiles_1d.j_total
- ids.profiles_1d.j_bootstrap
- ids.profiles_1d.conductivity_parallel
