# Landscape Client CPU Profiling

## Setup

This project uses `poetry` to manage dependencies.

```bash
# Install poetry if needed
pip install poetry

# Install project dependencies (automatically creates and manages venv)
poetry install
```

You'll need to create Landscape server and client images in LXD. These are required inputs to the Terraform plan. The client image needs to be for a VM to ensure accurate CPU profiling.

### Landscape client

TODO write docs

### Landscape server

TODO write docs

## Inputs

See `variables.tf` for required inputs.

## Profiling

```bash
# Set environment variables

# Run the profiling test
poetry run pytest test_profiler.py
```

Infrastructure will automatically be torn down after a test run. Use `KEEP_TERRAFORM_INFRA` to keep infrastructure up after the test run finishes.

```bash
KEEP_TERRAFORM_INFRA=1 poetry run pytest test_profiler.py
```

## Outputs

Data will be collected in a `results/` directory. Subsequent runs will create a new timestamped directory.
