# Landscape Client CPU Profiling

## Setup

```bash
# Install poetry if needed
pip install poetry

# Install project dependencies (automatically creates and manages venv)
poetry install
```

## Inputs

See `variables.tf` for required inputs.

## Profiling

```bash
# Set environment variables

# Run the profiling test
poetry run pytest test_profiler.py
```
