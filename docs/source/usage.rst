.. _`usage`:

Running simulations with MUSCLE3
################################

For general MUSCLE3 workflow instructions, see the `MUSCLE3 documentation <https://muscle3.readthedocs.io/en/latest/>`_.

This page shows the specifications for the MUSCLE3 actor running the Torax core transport simulator.

Available Operational Modes
---------------------------

- **Torax actor**: Default.

.. code-block:: bash
  implementations:
    env:
      IMAS_VERSION: "4.0.0"
    torax:
      executable: python
      args: "-u -m torax_muscle3.torax_actor"

Available Settings
------------------

* Mandatory

  - **python_config_module**: (string) configuration module for torax

* Optional

  - **output_all_timeslices**: (string) Whether to send every internal TORAX timeslice as final O_F output instead of just the requested one. Defaults to False.
  - **use_IDS_plasma_composition**: (bool) whether to use plasma composition from input core_profiles IDS on F_INIT or from TORAX config. Defaults to False (i.e. use TORAX config).
  - **t_initial**: (float) starting time of TORAX actor.
  - **t_final**: (float) ending time of TORAX actor.
  - **fixed_dt**: (float) timestep of TORAX actor.
  - **communication_interval**: (float) time interval at which to send/receive data through MUSCLE3 connections. Common to all connected ports. Defaults to 1e-6 seconds.
  - **max_consecutive_invalid_input**: (int) abort the run if a single port receives ``output_flag == -1`` this many times in a row. Defaults to unset, i.e. tolerate invalid input indefinitely. See `Handling invalid input`_ below.

Handling invalid input
----------------------

Each received IDS carries ``code.output_flag``; a value of ``-1`` marks it as
invalid (e.g. the upstream producer's solve didn't converge for that step) and
the actor discards it rather than using it to advance the simulation. A
consecutive-invalid counter is kept per port; it is logged as a warning on
every invalid receive and reset to zero the next time that port receives a
valid message.

Occasional invalid input is expected in a co-simulation (a transient
reject/rollback in the upstream solver) and is tolerated silently by default.
If ``max_consecutive_invalid_input`` is set and a port's streak reaches it, the
actor raises instead of continuing to wait — this catches an upstream producer
that is stuck resending a rejected/stale step rather than recovering, which
would otherwise silently loop until some other timeout.

Simulated time window
---------------------

The simulated time window (``numerics.t_initial`` / ``numerics.t_final``) is
resolved from up to three sources, listed from lowest to highest precedence — a
later source overrides an earlier one key-by-key:

1. the ``numerics`` block in the TORAX config file (``python_config_module``);
2. the **first and last** ``time`` of the equilibrium sequence received on
   ``equilibrium_in_f`` on F_INIT, if that port is connected. This lets a coupled
   driver size the run from the data it sends, so the config file needs no
   scenario-specific time range;
3. the explicit ``t_initial`` / ``t_final`` ymmsl settings above, if set.

So an equilibrium-driven workflow can leave ``t_initial`` / ``t_final`` unset and
let the input data drive the window, while an operator can always pin the window
by setting them explicitly in the ymmsl. ``fixed_dt`` is never derived from the
equilibrium; it only comes from the config file or an explicit ymmsl setting. The
window source is reported in the actor log on F_INIT.

.. note::
   The window is taken from the equilibrium only. Workflows centered on a
   different IDS would need another source (e.g. the shortest window common to
   all received IDSs); this is not yet implemented.

Available Ports
---------------

The Torax actor currently only has IDS coupling functionality for both input and output for the following IDSs:
[equilibrium, core_profiles], and for output only for [core_sources].

* Optional

  - **<ids_name>_in_f (F_INIT)**: given IDS as initial input.
  - **<ids_name>_out_i (O_I)**: given IDS as inner loop output.
  - **<ids_name>_in_s (S)**: given IDS as inner loop input.
  - **<ids_name>_out_f (O_F)**: given IDS as final output.

General
-------
The torax actor can be used with IMAS DDv4.
