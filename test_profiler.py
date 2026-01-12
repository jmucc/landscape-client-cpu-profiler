"""
Pytest-based profiler for Landscape client CPU usage.

This is an incremental conversion from get_data.sh to make the profiling
process more maintainable using pytest fixtures.
"""

import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from conftest import RegisteredClient, ProfilingConfig


# Remote log paths on LXD instances
REMOTE_CLIENT_CPU_USAGE_LOG = "/home/ubuntu/cpu_usage.log"
REMOTE_CLIENT_DB_SIZE_LOG = "/home/ubuntu/db_size.log"
REMOTE_SERVER_PACKAGE_COUNTS_LOG = "/home/ubuntu/package_counts.log"
REMOTE_SERVER_PACKAGE_BUFFER_COUNTS_LOG = "/home/ubuntu/package_buffer_counts.log"

# Local results configuration
RESULTS_DIR = Path("./results")


@dataclass
class ProfilingResults:
    """Results from a profiling run."""

    cpu_usage: str
    db_size: str
    package_counts: str
    package_buffer_counts: str
    timestamp: datetime


def collect_client_cpu_usage(client_machine):
    """
    Collect CPU usage statistics for the client.
    """
    subprocess.run(
        [
            "lxc",
            "exec",
            client_machine,
            "--",
            "bash",
            "-c",
            "ps aux > /home/ubuntu/file.txt; "
            "grep landscape-package-reporter /home/ubuntu/file.txt | "
            f"awk '{{sum += $3}} END {{printf \"%.1f\\n\", sum}}' >> {REMOTE_CLIENT_CPU_USAGE_LOG}",
        ],
        check=True,
    )


def collect_client_package_database_size(client_machine):
    """
    Collect the size of the client's local package database.
    """
    subprocess.run(
        [
            "lxc",
            "exec",
            client_machine,
            "--",
            "bash",
            "-c",
            "wc /var/lib/landscape/client/package/database | "
            f"awk '{{print $3}}' >> {REMOTE_CLIENT_DB_SIZE_LOG}",
        ],
        check=True,
    )


def collect_package_counts_for_client(server_machine, client_id):
    """
    Collect package counts for computer with ID `client_id` from the server_machine's
    `computer_packages` table.

    NOTE: cd /tmp to avoid annoying output from psql trying to set homedir
    """
    subprocess.run(
        [
            "lxc",
            "exec",
            server_machine,
            "--",
            "bash",
            "-c",
            f'cd /tmp && sudo -u landscape psql -d landscape-standalone-resource-1 -c "'
            f"SELECT CARDINALITY(available) as len_available, "
            f"CARDINALITY(available_upgrades) as len_available_upgrades, "
            f"CARDINALITY(installed) as len_installed, "
            f"CARDINALITY(held) as len_held, "
            f"CARDINALITY(autoremovable) as len_autoremovable, "
            f"CARDINALITY(security) as len_security "
            f"FROM computer_packages WHERE computer_id={client_id}"
            f"\" | head -n 3 | tail -n 1 | sed 's/|/,/g' | sed 's/ //g' >> {REMOTE_SERVER_PACKAGE_COUNTS_LOG}",
        ],
        check=True,
    )


def collect_package_buffer_counts_for_client(server_machine, client_id):
    """
    Collect package buffer counts for computer with ID `client_id` from the
    server_machine's `computer_packages` table.

    NOTE: cd /tmp to avoid annoying output from psql trying to set homedir
    """
    subprocess.run(
        [
            "lxc",
            "exec",
            server_machine,
            "--",
            "bash",
            "-c",
            f'cd /tmp && sudo -u landscape psql -d landscape-standalone-resource-1 -c "'
            f"SELECT CARDINALITY(available) as len_available, "
            f"CARDINALITY(not_available) as len_not_available, "
            f"CARDINALITY(available_upgrades) as len_available_upgrades, "
            f"CARDINALITY(not_available_upgrades) as len_not_available_upgrades, "
            f"CARDINALITY(installed) as len_installed, "
            f"CARDINALITY(not_installed) as len_not_installed, "
            f"CARDINALITY(held) as len_held, "
            f"CARDINALITY(not_held) as len_not_held, "
            f"CARDINALITY(autoremovable) as len_autoremovable, "
            f"CARDINALITY(not_autoremovable) as len_not_autoremovable, "
            f"CARDINALITY(security) as len_security, "
            f"CARDINALITY(not_security) as len_not_security "
            f"FROM computer_packages_buffer WHERE computer_id={client_id}"
            f"\" | head -n 3 | tail -n 1 | sed 's/|/,/g' | sed 's/ //g' >> {REMOTE_SERVER_PACKAGE_BUFFER_COUNTS_LOG}",
        ],
        check=True,
    )


def pull_results(server_machine, client_machine):
    """
    Pull profiling results from LXD instances to local files.
    """
    timestamp = datetime.now()
    timestamp_str = timestamp.strftime("%a_%b_%d_%H:%M:%S")

    # Ensure results directory exists with timestamp
    results_dir = RESULTS_DIR / timestamp_str
    results_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📊 Pulling profiling results (timestamp: {timestamp_str})...")

    # Pull client results
    cpu_usage_file = str(results_dir / "cpu_usage.log")
    subprocess.run(
        [
            "lxc",
            "file",
            "pull",
            f"{client_machine}/{REMOTE_CLIENT_CPU_USAGE_LOG}",
            cpu_usage_file,
        ],
        check=True,
    )

    db_size_file = str(results_dir / "db_size.log")
    subprocess.run(
        [
            "lxc",
            "file",
            "pull",
            f"{client_machine}/{REMOTE_CLIENT_DB_SIZE_LOG}",
            db_size_file,
        ],
        check=True,
    )

    # Pull server results
    package_counts_file = str(results_dir / "package_counts.log")
    subprocess.run(
        [
            "lxc",
            "file",
            "pull",
            f"{server_machine}/{REMOTE_SERVER_PACKAGE_COUNTS_LOG}",
            package_counts_file,
        ],
        check=True,
    )

    package_buffer_counts_file = str(results_dir / "package_buffer_counts.log")
    subprocess.run(
        [
            "lxc",
            "file",
            "pull",
            f"{server_machine}/{REMOTE_SERVER_PACKAGE_BUFFER_COUNTS_LOG}",
            package_buffer_counts_file,
        ],
        check=True,
    )

    print("✅ Results retrieved successfully")
    return ProfilingResults(
        cpu_usage=cpu_usage_file,
        db_size=db_size_file,
        package_counts=package_counts_file,
        package_buffer_counts=package_buffer_counts_file,
        timestamp=timestamp,
    )


def test_profile_landscape_client(
    registered_client: RegisteredClient,
    profiling_config: ProfilingConfig,
):
    """
    Main profiling test that runs the CPU profiling loop.
    """

    start_time = datetime.now()
    print(f"\nStarting CPU profiling for { profiling_config.iterations} iterations...")

    for _ in tqdm(range(profiling_config.iterations)):
        collect_client_cpu_usage(registered_client.client_lxd_instance_name)
        collect_client_package_database_size(registered_client.client_lxd_instance_name)
        collect_package_counts_for_client(
            server_machine=registered_client.server_lxd_instance_name,
            client_id=registered_client.client_id,
        )
        collect_package_buffer_counts_for_client(
            server_machine=registered_client.server_lxd_instance_name,
            client_id=registered_client.client_id,
        )
        time.sleep(profiling_config.iteration_delay_seconds)

    end_time = datetime.now()
    print(f"CPU profiling completed. Start time: {start_time}, End time: {end_time}")

    results = pull_results(
        server_machine=registered_client.server_lxd_instance_name,
        client_machine=registered_client.client_lxd_instance_name,
    )

    print(f"\n✅ Profiling test completed successfully!")
    print(f"📁 Results saved:")
    print(f"   - cpu_usage: {results.cpu_usage}")
    print(f"   - db_size: {results.db_size}")
    print(f"   - package_counts: {results.package_counts}")
    print(f"   - package_buffer_counts: {results.package_buffer_counts}")
