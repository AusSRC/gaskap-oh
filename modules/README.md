# Modules

Here are code snippets that can be run in the pipeline. They are imported as modules of the main workflow, but can also be run separately for development purposes.

## Setup

First read the [README.md](../README.md) file at the root of the project for instructions on setting up a Python virtual environment. Once it has been setup, install the dependencies in the `requirements.txt` file:

```
source /path/to/venv/bin/activate
pip install -r requirements.txt
```

## Usage

**NOTE: This is a setup for iterating in development**

For a given run, you can experiment with the parameters for the sidelobe rejection workflow by updating the code manually here outside of the pipeline. To run the sidelobe rejection workflow:

```
python modules/sidelobe_rejection.py config/sofiax.ini
```

Then you are able to clear the choices made in this run of the workflow with:

```
python modules/reset_run.py config/sofiax.ini
```
