"""
Pytest-based profiler for Landscape client CPU usage.

This is an incremental conversion from get_data.sh to make the profiling
process more maintainable using pytest fixtures.
"""

import subprocess
import time
from datetime import datetime

from conftest import RegisteredClient, ProfilingConfig



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
            "awk '{sum += $3} END {printf \"%.1f\\n\", sum}' >> /home/ubuntu/cpu_usage.log",
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
            "awk '{print $3}' >> /home/ubuntu/db_size.log",
        ],
        check=True,
    )


def collect_package_counts_for_client(server_machine, client_id):
    """
    Collect package counts for computer with ID `client_id` from the server_machine's
    `computer_packages` table.
    """
    subprocess.run(
        [
            "lxc",
            "exec",
            server_machine,
            "--",
            "bash",
            "-c",
            f'sudo -u landscape psql -d landscape-standalone-resource-1 -c "'
            f"SELECT CARDINALITY(available) as len_available, "
            f"CARDINALITY(available_upgrades) as len_available_upgrades, "
            f"CARDINALITY(installed) as len_installed, "
            f"CARDINALITY(held) as len_held, "
            f"CARDINALITY(autoremovable) as len_autoremovable, "
            f"CARDINALITY(security) as len_security "
            f"FROM computer_packages WHERE computer_id={client_id}"
            f"\" | head -n 3 | tail -n 1 | sed 's/|/,/g' | sed 's/ //g' >> /home/ubuntu/package_counts.log",
        ],
        check=True,
    )


def collect_package_buffer_counts_for_client(server_machine, client_id):
    """
    Collect package buffer counts for computer with ID `client_id` from the
    server_machine's `computer_packages` table.
    """
    subprocess.run(
        [
            "lxc",
            "exec",
            server_machine,
            "--",
            "bash",
            "-c",
            f'sudo -u landscape psql -d landscape-standalone-resource-1 -c "'
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
            f"\" | head -n 3 | tail -n 1 | sed 's/|/,/g' | sed 's/ //g' >> /home/ubuntu/package_buffer_counts.log",
        ],
        check=True,
    )


def pull_results(server_machine, client_machine):
    """
    Pull profiling results from LXD instances to local files.
    """
    timestamp = datetime.now().strftime("%a_%b_%d_%H:%M:%S_%Z_%Y")

    print(f"\n📊 Pulling profiling results (timestamp: {timestamp})...")

    results = {}

    # Pull client results
    for log_name, log_file in [
        ("cpu_usage", "cpu_usage.log"),
        ("db_size", "db_size.log"),
    ]:
        local_file = f"./{log_name}_{timestamp}.log"
        subprocess.run(
            [
                "lxc",
                "file",
                "pull",
                f"{client_machine}/home/ubuntu/{log_file}",
                local_file,
            ],
            check=True,
        )
        results[log_name] = local_file

    # Pull server results
    for log_name, log_file in [
        ("package_counts", "package_counts.log"),
        ("package_buffer_counts", "package_buffer_counts.log"),
    ]:
        local_file = f"./{log_name}_{timestamp}.log"
        subprocess.run(
            [
                "lxc",
                "file",
                "pull",
                f"{server_machine}/home/ubuntu/{log_file}",
                local_file,
            ],
            check=True,
        )
        results[log_name] = local_file

    print("✅ Results retrieved successfully")
    return results


def test_profile_landscape_client(
    registered_client: RegisteredClient,
    profiling_config: ProfilingConfig,
):
    """
    Main profiling test that runs the CPU profiling loop.
    """
    # Extract configuration from fixtures
    server_machine = registered_client.server_name
    client_machine = registered_client.client_name
    client_id = registered_client.client_id

    profiling_iterations = profiling_config.iterations

    start_time = datetime.now()
    print(f"\nStarting CPU profiling for {profiling_iterations} iterations...")

    # Main profiling loop
    for i in range(1, profiling_iterations + 1):
        collect_client_cpu_usage(client_machine)
        collect_client_package_database_size(client_machine)
        collect_package_counts_for_client(server_machine, client_id)
        collect_package_buffer_counts_for_client(server_machine, client_id)

        if i % 10 == 0:
            print(f"  Completed iteration {i}/{profiling_iterations}")

        time.sleep(profiling_config.iteration_delay_seconds)

    end_time = datetime.now()
    print(f"CPU profiling completed. Start time: {start_time}, End time: {end_time}")

    results = pull_results(server_machine, client_machine)

    print(f"\n✅ Profiling test completed successfully!")
    print(f"📁 Results saved:")
    for result_type, file_path in results.items():
        print(f"   - {result_type}: {file_path}")
