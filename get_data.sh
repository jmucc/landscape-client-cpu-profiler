#!/bin/bash
if [ -z "${SERVER_CONTAINER_IMAGE_NAME}" ]; then
    echo "ERROR: SERVER_CONTAINER_IMAGE_NAME environment variable is not set."
    exit 1
fi

if [ -z "${REGISTRATION_KEY}" ]; then
    echo "ERROR: REGISTRATION_KEY environment variable is not set."
    exit 1
fi

profiling_iterations=$1

server_machine="profiling-landscape-server"
server_ip=$(lxc list ${server_machine} -c 4 | grep eth0 | awk '{print $2}')
server_hostname="${SERVER_CONTAINER_IMAGE_NAME}.lxd"
client_machine="profiling-landscape-client"
client_lxd_instance_name="cpu-profiling"

lxc exec ${client_machine} -- sudo bash -c "echo ${server_ip} ${server_hostname} >> /etc/hosts"

# SSL handshake
lxc exec ${client_machine} -- bash -c \
    "echo | openssl s_client -connect ${server_hostname}:443 | openssl x509 | sudo tee /etc/landscape/server.pem"

# Register client with server
lxc exec ${client_machine} -- sudo landscape-config --silent \
    --account-name="standalone" \
    --computer-title="${client_lxd_instance_name}" \
    --registration-key="${REGISTRATION_KEY}" \
    --ping-url="http://${server_hostname}/ping" \
    --url="https://${server_hostname}/message-system" \
    --ssl-public-key="/etc/landscape/server.pem" \
    --ping-interval=10 \
    --exchange-interval=10 \
    --urgent-exchange-interval=10 \
    --log-level="debug"

# Grab client id
client_id=$(lxc exec ${server_machine} -- bash -c "
    sudo -u landscape psql -d landscape-standalone-main -c \
    \"SELECT id FROM computer WHERE title='${client_lxd_instance_name}'\" | head -n 3 | tail -n 1 | sed 's/ //g'
")

start=$(date)
echo "Starting CPU profiling for ${profiling_iterations} iterations..."
for i in $(seq 1 ${profiling_iterations})
do
    # CPU usage
    lxc exec ${client_machine} -- bash -c "
        ps aux > /home/ubuntu/file.txt;
        grep landscape-package-reporter /home/ubuntu/file.txt | awk '{sum += \$3} END {printf \"%.1f\\n\", sum}' >> /home/ubuntu/cpu_usage.log;
    "

    # Client package DB size
    lxc exec ${client_machine} -- bash -c "
        wc /var/lib/landscape/client/package/database | awk '{print \$3}' >> /home/ubuntu/db_size.log
    "

    # Server package DB counts
    lxc exec ${server_machine} -- bash -c "
        sudo -u landscape psql -d landscape-standalone-resource-1 -c \"
            SELECT CARDINALITY(available) as len_available, 
                   CARDINALITY(available_upgrades) as len_available_upgrades, 
                   CARDINALITY(installed) as len_installed, 
                   CARDINALITY(held) as len_held, 
                   CARDINALITY(autoremovable) as len_autoremovable, 
                   CARDINALITY(security) as len_security
            FROM computer_packages
            WHERE computer_id=${client_id}
        \" | head -n 3 | tail -n 1 | sed 's/|/,/g' | sed 's/ //g' >> /home/ubuntu/package_counts.log
    "

    lxc exec ${server_machine} -- bash -c "
        sudo -u landscape psql -d landscape-standalone-resource-1 -c \"
            SELECT CARDINALITY(available) as len_available, 
                   CARDINALITY(not_available) as len_not_available,
                   CARDINALITY(available_upgrades) as len_available_upgrades, 
                   CARDINALITY(not_available_upgrades) as len_not_available_upgrades, 
                   CARDINALITY(installed) as len_installed, 
                   CARDINALITY(not_installed) as len_not_installed, 
                   CARDINALITY(held) as len_held, 
                   CARDINALITY(not_held) as len_not_held, 
                   CARDINALITY(autoremovable) as len_autoremovable, 
                   CARDINALITY(not_autoremovable) as len_not_autoremovable, 
                   CARDINALITY(security) as len_security,
                   CARDINALITY(not_security) as len_not_security
            FROM computer_packages_buffer
            WHERE computer_id=${client_id}
        \" | head -n 3 | tail -n 1 | sed 's/|/,/g' | sed 's/ //g' >> /home/ubuntu/package_buffer_counts.log
    "

    sleep 0.5
done
ending=$(date)

echo "CPU profiling completed. Start time: ${start}, End time: ${ending}"

# Pull results
lxc file pull ${client_machine}/home/ubuntu/cpu_usage.log ./cpu_usage_$(echo $ending | sed 's/ /_/g').log
lxc file pull ${client_machine}/home/ubuntu/db_size.log ./db_size_$(echo $ending | sed 's/ /_/g').log  
lxc file pull ${server_machine}/home/ubuntu/package_counts.log ./package_counts_$(echo $ending | sed 's/ /_/g').log
lxc file pull ${server_machine}/home/ubuntu/package_buffer_counts.log ./package_buffer_counts_$(echo $ending | sed 's/ /_/g').log