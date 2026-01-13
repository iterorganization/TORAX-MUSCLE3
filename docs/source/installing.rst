.. _`installing`:

Installing TORAX-MUSCLE3
========================

User installation
-------------------

  .. code-block:: bash

    pip install torax-muscle3

SDCC installation
-----------------

* Setup a project folder and clone git repository

  .. code-block:: bash

    mkdir projects
    cd projects
    git clone git@github.com:iterorganization/TORAX-MUSCLE3.git
    cd TORAX-MUSCLE3

* Setup a python virtual environment and install python dependencies

  .. code-block:: bash

    module load Python

    python3 -m venv ./venv
    . venv/bin/activate
    pip install --upgrade pip
    pip install --upgrade wheel setuptools
    # For development an installation in editable mode may be more convenient
    pip install .[all]

    python3 -c "import torax_muscle3; print(torax_muscle3.__version__)"
    pytest

Ubuntu installation
-------------------

* Install system packages

  .. code-block:: bash

    sudo apt update
    sudo apt install build-essential git-all python3-dev python-is-python3 \
      python3 python3-venv python3-pip python3-setuptools

* Setup a project folder and clone git repository

  .. code-block:: bash

    mkdir projects
    cd projects
    git clone git@github.com:iterorganization/TORAX-MUSCLE3.git
    cd TORAX-MUSCLE3

* Setup a python virtual environment and install python dependencies

  .. code-block:: bash

    python3 -m venv ./venv
    . venv/bin/activate
    pip install --upgrade pip
    pip install --upgrade wheel setuptools
    # For development an installation in editable mode may be more convenient
    pip install .[all]

    pytest

Documentation
-------------

* To build the TORAX-MUSCLE3 documentation, execute:

  .. code-block:: bash

    make -C docs html
