"""
Pytest fixtures for Landscape client CPU profiling.

This file contains shared fixtures that abstract infrastructure setup
and teardown operations.
"""

import json
import os
import subprocess
import time
from typing import Generator
from dataclasses import dataclass
import pytest


@dataclass
class TerraformOutputs:
    """Dataclass containing all Terraform deployment outputs."""

    server_name: str
    """
    Name of the LXD server instance.
    """
    
    client_name: str
    """
    Name of the LXD client instance.
    """
    
    server_image: str
    """
    Identifier for the LXD image used to spawn the server instance.
    """
    
    client_image: str
    """
    Identifier for the LXD image used to spawn the client instance.
    """
    
    server_ipv4_address: str
    """
    IP address of the server instance.
    """
    
    client_ipv4_address: str
    """
    IP address of the client instance.
    """

    @property
    def server_hostname(self) -> str:
        """Construct server hostname from server image name."""
        return f"{self.server_image}.lxd"

    @classmethod
    def from_terraform_json(cls, tf_json: dict) -> "TerraformOutputs":
        """Create TerraformOutputs from terraform output -json result."""
        return cls(
            server_name=tf_json["server_name"]["value"],
            client_name=tf_json["client_name"]["value"],
            server_image=tf_json["server_image"]["value"],
            client_image=tf_json["client_image"]["value"],
            server_ipv4_address=tf_json["server_ipv4_address"]["value"],
            client_ipv4_address=tf_json["client_ipv4_address"]["value"],
        )


@dataclass
class RegisteredClient:
    """
    Data for a client that has been registered with the server.
    """

    server_name: str
    """
    The LXD instance name of the server.
    """

    client_name: str
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

    iterations: int = 500
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

    landscape_registration_key: str = "landscapeisgreat"
    account_name: str = "standalone"
    client_name: str = "cpu-profiler-client"
    ping_interval: int = 10
    exchange_interval: int = 10
    urgent_exchange_interval: int = 10
    log_level: str = "debug"


@pytest.fixture(scope="session")
def terraform_outputs() -> Generator[TerraformOutputs]:
    """
    Deploy Terraform infrastructure and return outputs.
    """
    print("\n🚀 Deploying Terraform infrastructure...")
    subprocess.run(["terraform", "init"], check=True, cwd=os.getcwd())
    subprocess.run(["terraform", "apply", "-auto-approve"], check=True, cwd=os.getcwd())

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
    print(f"   Server: {outputs.server_name} ({outputs.server_ipv4_address})")
    print(f"   Client: {outputs.client_name} ({outputs.client_ipv4_address})")

    yield outputs

    print("\n🧹 Tearing down Terraform infrastructure...")
    subprocess.run(
        ["terraform", "destroy", "-auto-approve"], check=True, cwd=os.getcwd()
    )
    print("✅ Infrastructure cleaned up")


@pytest.fixture(scope="session")
def profiling_config() -> ProfilingConfig:
    return ProfilingConfig()


def get_client_id(server_machine: str, client_name: str) -> str:
    """
    Helper function to retrieve the client ID from the server database.
    """
    result = subprocess.run(
        [
            "lxc",
            "exec",
            server_machine,
            "--",
            "bash",
            "-c",
            f"sudo -u landscape psql -d landscape-standalone-main -c "
            f"\"SELECT id FROM computer WHERE title='{client_name}'\" "
            f"| head -n 3 | tail -n 1 | sed 's/ //g'",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    client_id = result.stdout.strip()
    assert client_id, "Failed to retreive client ID from database."

    return client_id


@pytest.fixture(scope="function")
def registered_client(
    terraform_outputs: TerraformOutputs,
    client_config: ClientConfig,
) -> RegisteredClient:
    """
    Fixture that handles client registration with the Landscape server.

    This fixture:
    - Adds server hostname to client's /etc/hosts
    - Performs SSL handshake to get server certificate
    - Registers client with the server using landscape-config
    - Retrieves and returns the client ID
    - Cleans up log files before profiling
    """
    server_machine = terraform_outputs.server_name
    client_machine = terraform_outputs.client_name
    server_ip = terraform_outputs.server_ipv4_address
    server_hostname = terraform_outputs.server_hostname
    client_name = client_config.client_name
    registration_key = client_config.landscape_registration_key

    print(f"\n📝 Registering client '{client_name}' with server...")

    # Add server to client's /etc/hosts
    subprocess.run(
        [
            "lxc",
            "exec",
            client_machine,
            "--",
            "sudo",
            "bash",
            "-c",
            f"echo {server_ip} {server_hostname} >> /etc/hosts",
        ],
        check=True,
    )

    # SSL handshake - get server certificate
    subprocess.run(
        [
            "lxc",
            "exec",
            client_machine,
            "--",
            "bash",
            "-c",
            f"echo | openssl s_client -connect {server_hostname}:443 | "
            f"openssl x509 | sudo tee /etc/landscape/server.pem",
        ],
        check=True,
    )

    # Register client with server
    subprocess.run(
        [
            "lxc",
            "exec",
            client_machine,
            "--",
            "sudo",
            "landscape-config",
            "--silent",
            "--account-name=standalone",
            f"--computer-title={client_name}",
            f"--registration-key={registration_key}",
            f"--ping-url=http://{server_hostname}/ping",
            f"--url=https://{server_hostname}/message-system",
            "--ssl-public-key=/etc/landscape/server.pem",
            "--ping-interval=10",
            "--exchange-interval=10",
            "--urgent-exchange-interval=10",
            "--log-level=debug",
        ],
        check=True,
    )

    print("⏳ Waiting for client to appear in database...")
    # Give it a moment for the registration to complete
    time.sleep(5)

    # Get client ID
    client_id = get_client_id(server_machine, client_name)
    print(f"✅ Client registered with ID: {client_id}")

    # Clean up any existing log files from previous runs
    # TODO remove these - won't be necessary on fresh infra.
    for log_file in ["cpu_usage.log", "db_size.log"]:
        subprocess.run(
            [
                "lxc",
                "exec",
                client_machine,
                "--",
                "bash",
                "-c",
                f"rm -f /home/ubuntu/{log_file}",
            ],
            check=False,
        )  # Don't fail if files don't exist

    for log_file in ["package_counts.log", "package_buffer_counts.log"]:
        subprocess.run(
            [
                "lxc",
                "exec",
                server_machine,
                "--",
                "bash",
                "-c",
                f"rm -f /home/ubuntu/{log_file}",
            ],
            check=False,
        )  # Don't fail if files don't exist

    return RegisteredClient(
        server_name=server_hostname,
        client_name=client_machine,
        client_id=int(client_id),
    )
