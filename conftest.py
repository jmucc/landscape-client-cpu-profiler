"""
Pytest fixtures for Landscape client CPU profiling.

This file contains shared fixtures that abstract infrastructure setup
and teardown operations.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Generator
from dataclasses import dataclass
import pytest
import tomllib


def load_profiler_config() -> Dict[str, Any]:
    """
    Load profiler configuration from pyproject.toml.
    """
    pyproject_path = Path(__file__).parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)

    profiler_config = pyproject_data.get("tool", {}).get("profiler", {})

    assert profiler_config, "Missing tool.profiler configuration in pyproject.toml"

    return profiler_config


@dataclass
class TerraformOutputs:
    """Dataclass containing all Terraform deployment outputs."""

    server_lxd_instance_name: str
    """
    Name of the LXD server instance.
    """

    client_lxd_instance_name: str
    """
    Name of the LXD client instance.
    """

    server_certificate_hostname: str
    """
    Hostname on the server's certificate. Generally this is the same as the name of the
    container instance that was used to publish the image.
    """

    pro_token: str
    """
    Optionally, a pro token to attach to the client.
    """

    server_ipv4_address: str
    """
    IP address of the server instance.
    """

    client_ipv4_address: str
    """
    IP address of the client instance.
    """

    @classmethod
    def from_terraform_json(cls, tf_json: dict) -> "TerraformOutputs":
        """Create TerraformOutputs from terraform output -json result."""
        return cls(
            server_lxd_instance_name=tf_json["server_lxd_instance_name"]["value"],
            client_lxd_instance_name=tf_json["client_lxd_instance_name"]["value"],
            server_certificate_hostname=tf_json["server_certificate_hostname"]["value"],
            pro_token=tf_json["pro_token"]["value"],
            server_ipv4_address=tf_json["server_ipv4_address"]["value"],
            client_ipv4_address=tf_json["client_ipv4_address"]["value"],
        )


@dataclass
class RegisteredClient:
    """
    Data for a client that has been registered with the server.
    """

    server_lxd_instance_name: str
    """
    The LXD instance name of the server.
    """

    client_lxd_instance_name: str
    """
    The LXD instance name of the client.
    """

    client_id: int
    """
    The client ID in the server database.
    """


@dataclass
class ProfilingConfig:
    """
    Configuration for the profiler.
    """

    iterations: int = 60
    """
    How many iterations to run the profiler. This determines the number of datapoints.
    """

    iteration_delay_seconds: float = 0.5
    """
    The delay between iterations, in seconds.
    """


@dataclass
class ClientConfig:
    """
    Configuration for the client machine used in the profiling run.
    """

    computer_title: str = "cpu-profiler-client"
    ping_interval: int = 10
    exchange_interval: int = 10
    urgent_exchange_interval: int = 10
    log_level: str = "debug"


@dataclass
class InfraConfig:
    """
    Configuration for the infrastructure used in the test.
    """

    keep_infrastructure: bool


@dataclass
class AccountConfig:
    """
    Configuration for bootstrapping the Landscape account.
    """

    landscape_registration_key: str = "landscapeisgreat"
    admin_email: str = "admin@example.com"
    admin_name: str = "Admin User"
    admin_password: str = "admin123"
    system_email: str = "landscape@example.com"


@pytest.fixture(scope="session")
def profiling_config() -> ProfilingConfig:
    """
    Parse `profiler` configuration from the pyproject.toml
    """
    config = load_profiler_config()
    profiling_data = config.get("profiling", {})
    return ProfilingConfig(**profiling_data)


@pytest.fixture(scope="session")
def client_config() -> ClientConfig:
    """
    Parse `client` configuration from the pyproject.toml
    """
    config = load_profiler_config()
    client_data = config.get("client", {})
    return ClientConfig(**client_data)


@pytest.fixture(scope="session")
def infra_config() -> InfraConfig:
    """
    Parse `infra` configuration from the pyproject.toml
    """
    config = load_profiler_config()
    terraform_config = config.get("infra", {})
    return InfraConfig(**terraform_config)


@pytest.fixture(scope="session")
def terraform_outputs(
    infra_config: InfraConfig,
) -> Generator[TerraformOutputs, None, None]:
    """
    Deploy Terraform infrastructure and return outputs.
    """
    print("\n🚀 Deploying Terraform infrastructure...")
    subprocess.run(["terraform", "init"], check=True, cwd=os.getcwd())

    # Clean up any existing infrastructure first
    print("🧹 Cleaning up any existing infrastructure...")
    subprocess.run(
        ["terraform", "destroy", "-auto-approve"],
        check=False,
        cwd=os.getcwd(),
    )

    subprocess.run(
        ["terraform", "apply", "-auto-approve"],
        check=True,
        cwd=os.getcwd(),
    )

    # Get Terraform outputs
    result = subprocess.run(
        ["terraform", "output", "-json"],
        capture_output=True,
        text=True,
        check=True,
        cwd=os.getcwd(),
    )
    tf_json = json.loads(result.stdout)
    outputs = TerraformOutputs.from_terraform_json(tf_json)
    print("✅ Terraform infrastructure deployed")

    yield outputs

    if infra_config.keep_infrastructure:
        print("\nNot tearing down Terraform infastructure.")
    else:
        print("\n🧹 Tearing down Terraform infrastructure...")
        subprocess.run(
            ["terraform", "destroy", "-auto-approve"], check=True, cwd=os.getcwd()
        )
        print("✅ Infrastructure cleaned up.")


def get_client_id(server_machine: str, computer_title: str, timeout: int = 30) -> int:
    """
    Helper function to retrieve the client ID from the server database.
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        result = subprocess.run(
            [
                "lxc",
                "exec",
                server_machine,
                "--",
                "bash",
                "-c",
                f"sudo -u landscape psql -d landscape-standalone-main -c "
                f"\"SELECT id FROM computer WHERE title='{computer_title}'\" "
                f"| head -n 3 | tail -n 1 | sed 's/ //g'",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        client_id = result.stdout.strip()

        if client_id:
            try:
                return int(client_id)
            except ValueError:
                pass

        time.sleep(2)

    raise TimeoutError(
        f"Failed to retrieve client ID for '{computer_title}' after {timeout} seconds"
    )


def register_landscape_client(
    client_lxd_instance_name: str,
    client_computer_title: str,
    registration_key: str,
    server_certificate_hostname: str,
    max_retries: int = 3,
) -> None:
    """Register client with Landscape server."""
    for attempt in range(max_retries):
        try:
            subprocess.run(
                [
                    "lxc",
                    "exec",
                    client_lxd_instance_name,
                    "--",
                    "sudo",
                    "landscape-config",
                    "--silent",
                    f"--account-name=standalone",
                    f"--computer-title={client_computer_title}",
                    f"--registration-key={registration_key}",
                    f"--ping-url=http://{server_certificate_hostname}/ping",
                    f"--url=https://{server_certificate_hostname}/message-system",
                    "--ssl-public-key=/etc/landscape/server.pem",
                    "--ping-interval=10",
                    "--exchange-interval=10",
                    "--urgent-exchange-interval=10",
                    "--log-level=debug",
                ],
                check=True,
            )
            return
        except subprocess.CalledProcessError as e:
            if attempt < max_retries - 1:
                print(f"   Registration attempt {attempt + 1} failed, retrying...")
                time.sleep(5)
            else:
                raise RuntimeError(
                    f"Failed to register client after {max_retries} attempts"
                ) from e


@pytest.fixture(scope="session")
def registered_client(
    terraform_outputs: TerraformOutputs,
    client_config: ClientConfig,
    account_config: AccountConfig,
    bootstrap_account,
) -> RegisteredClient:
    """
    Register the client with the Landscape server.

    This fixture:
    - Adds server hostname to client's /etc/hosts
    - Performs SSL handshake to get server certificate
    - Registers client with the server using landscape-config
    - Retrieves and returns the client ID
    """

    server_lxd_instance_name = terraform_outputs.server_lxd_instance_name
    client_lxd_instance_name = terraform_outputs.client_lxd_instance_name
    server_ip = terraform_outputs.server_ipv4_address
    server_certificate_hostname = terraform_outputs.server_certificate_hostname
    client_computer_title = client_config.computer_title
    registration_key = account_config.landscape_registration_key

    print(f"\n📝 Registering client '{client_computer_title}' with server...")

    # Add server to client's /etc/hosts
    subprocess.run(
        [
            "lxc",
            "exec",
            client_lxd_instance_name,
            "--",
            "sudo",
            "bash",
            "-c",
            f"echo {server_ip} {server_certificate_hostname} >> /etc/hosts",
        ],
        check=True,
    )

    # SSL handshake - get server certificate
    subprocess.run(
        [
            "lxc",
            "exec",
            client_lxd_instance_name,
            "--",
            "bash",
            "-c",
            f"echo | openssl s_client -connect {server_certificate_hostname}:443 | "
            f"openssl x509 | sudo tee /etc/landscape/server.pem",
        ],
        check=True,
    )

    if pro_token := terraform_outputs.pro_token:
        subprocess.run(
            [
                "lxc",
                "exec",
                client_lxd_instance_name,
                "--",
                "sudo",
                "pro",
                "attach",
                pro_token,
            ],
            check=True,
        )
    else:
        print("Not attaching pro token. Assuming client image is entitled.")

    # Register client with server
    register_landscape_client(
        client_lxd_instance_name,
        client_computer_title,
        registration_key,
        server_certificate_hostname,
    )

    print("⏳ Waiting for client to appear in database...")

    # Get client ID
    client_id = get_client_id(server_lxd_instance_name, client_computer_title)
    print(f"✅ Client registered with ID: {client_id}")

    return RegisteredClient(
        server_lxd_instance_name=server_lxd_instance_name,
        client_lxd_instance_name=client_lxd_instance_name,
        client_id=client_id,
    )


@pytest.fixture(scope="session")
def account_config() -> AccountConfig:
    config = load_profiler_config()
    account_data = config.get("account", {})
    return AccountConfig(**account_data)


@pytest.fixture(scope="session")
def bootstrap_account(
    terraform_outputs: TerraformOutputs,
    account_config: AccountConfig,
) -> None:
    """
    Create the first Landscape account on the server.
    """
    BOOTSTRAP_ACCOUNT_SCRIPT = "/opt/canonical/landscape/bootstrap-account"
    server_lxd_instance_name = terraform_outputs.server_lxd_instance_name
    server_hostname = terraform_outputs.server_certificate_hostname
    root_url = f"https://{server_hostname}"
    max_retries = 3

    print(f"\n🔐 Bootstrapping Landscape account on server...")

    for attempt in range(max_retries):
        try:
            subprocess.run(
                [
                    "lxc",
                    "exec",
                    server_lxd_instance_name,
                    "--",
                    BOOTSTRAP_ACCOUNT_SCRIPT,
                    "--admin_email",
                    account_config.admin_email,
                    "--admin_name",
                    account_config.admin_name,
                    "--admin_password",
                    account_config.admin_password,
                    "--registration_key",
                    account_config.landscape_registration_key,
                    "--root_url",
                    root_url,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            print(f"✅ Account bootstrapped successfully")
            return
        except subprocess.CalledProcessError as e:
            print(
                f"   Bootstrap attempt {attempt + 1} failed (exit code {e.returncode})"
            )
            print(f"   stdout: {e.stdout}")
            print(f"   stderr: {e.stderr}")
            if attempt < max_retries - 1:
                print(f"   Retrying in 5 seconds...")
                time.sleep(5)
            else:
                raise RuntimeError(
                    f"Failed to bootstrap account after {max_retries} attempts. "
                    f"Last error: {e.stderr}"
                ) from e
