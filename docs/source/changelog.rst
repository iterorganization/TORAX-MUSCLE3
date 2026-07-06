.. _changelog:

Changelog
=========

Unreleased
----------

- Take the simulated time window (``t_initial``/``t_final``) from the first/last
  ``time`` of the equilibrium received on ``equilibrium_in_f``, unless overridden
  by explicit ymmsl numerics settings. See :ref:`usage` for the precedence order.

TORAX-MUSCLE3 0.1.2
------------------

- Only import ymmsl typehints during type checking

TORAX-MUSCLE3 0.1.1
------------------

- Fixed Torax version at 1.3.0

TORAX-MUSCLE3 0.1.0
------------------

Features
''''''''

- equilibrium IDS coupling
- core_profiles IDS coupling
- All coupled IDSs available on all MUSCLE3 ports with full flexibility
- compatible with IMAS DD v4
