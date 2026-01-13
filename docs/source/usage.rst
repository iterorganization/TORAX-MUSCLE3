.. _`usage`:

Running simulations with MUSCLE3
################################

For general MUSCLE3 workflow instructions, see the `MUSCLE3 documentation <https://muscle3.readthedocs.io/en/latest/>`_.

This page shows the specifications for the MUSCLE3 actor running the Torax core transport simulator.

Available Operational Modes
---------------------------

- ***Torax actor***: Default.

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

  - ***python_config_module***: (string) configuration module for torax

* Optional

  - ***output_all_timeslices***: (string) IMAS Data Dictionary version number to which data will be converted. Defaults to original dd_version of the data.

Available Ports
---------------

The Torax actor currently only has IDS coupling functionality for both input and output for the following IDSs:
[equilibrium, core_profiles].

* Optional

  - ***<ids_name>_f_init (F_INIT)***: given IDS as initial input.
  - ***<ids_name>_o_i (O_I)***: given IDS as inner loop output.
  - ***<ids_name>_s (S)***: given IDS as inner loop input.
  - ***<ids_name>_o_f (O_F)***: given IDS as final output.

General
-------
The torax actor can be used with IMAS DDv4.
