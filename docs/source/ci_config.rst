.. _`ci configuration`:

CI configuration
================

TORAX-MUSCLE3 uses github for CI. This page provides an overview
of the CI Plan and deployment projects.

CI Plan
-------

The TORAX-MUSCLE3 CI plan consists of 3 types of jobs:

Linting 
    Run ``ruff`` and ``mypy`` on the TORAX-MUSCLE3 code base.
    See :ref:`code style and linting`.

Testing
    This runs all unit tests with pytest.

Build docs
    This job builds the Sphinx documentation.
