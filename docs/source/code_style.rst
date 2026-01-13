.. _`code style and linting`:

Code style and linting
======================


Code style
----------

TORAX-MUSCLE3 follows `The Black Code Style
<https://black.readthedocs.io/en/stable/the_black_code_style/index.html>`_. All Python
files should be formatted with the ``ruff`` command line tool (this is checked in
:ref:`CI <ci configuration>`).


Why Ruff?
''''''''''

We use the ruff autoformatter, so the code style is uniform across all Python files,
regardless of the developer that created the code 🙂.

This improves efficiency of developers working on the project:

-   Uniform code style makes it easier to read, review and understand other's code.
-   Autoformatting code means that developers can save time and mental energy for the
    important matters.

More reasons for using ruff can be found on `their website
<https://docs.astral.sh/ruff/>`_.


Using Black
'''''''''''

The easiest way to work with Black is by using an integration with your editor. See
https://docs.astral.sh/ruff/integrations/.

You can also ``pip install ruff`` and run it every time before committing (manually or
with pre-commit hooks):

.. code-block:: console

    $ ruff check --fix torax_muscle3
    All checks passed!
    $ ruff format torax_muscle3
    6 files left unchanged.


Using mypy
''''''''''

.. code-block:: console

    $ mypy torax-m3
    Success: no issues found in 6 source files
