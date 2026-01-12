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

Example client image creation:

```bash
lxc launch ubuntu:noble client --vm
lxc exec client -- apt install -y landscape-client
lxc stop client
lxc publish client --alias client-image
```

You would use `client-image` in the Terraform inputs.

>[!NOTE]
>You may also attach a pro token in the image instead of providing one in the Terraform inputs.

### Landscape server

Example server image creation:

```bash
lxc launch ubuntu:noble server
lxc exec server -- add-apt-repository -y ppa:landscape/self-hosted-daily
lxc exec server -- DEBIAN_FRONTEND=noninteractive apt install landscape-server-quickstart
lxc stop server
lxc publish server --alias server-image
```

You would use `server-image` in the Terraform inputs.

## Inputs and configuration

See `variables.tf` for required Terraform inputs. See `pyproject.toml` for configuration options for the profiler tool.

## Profiling

Run the profiling tests using `poetry` and `pytest`:

```bash
poetry run pytest test_profiler.py
```

## Outputs

Data will be collected in a `results/` directory. Subsequent runs will create a new timestamped directory.
