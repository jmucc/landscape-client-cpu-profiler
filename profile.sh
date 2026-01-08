#!/bin/bash

client_machine="tf-landscape-client-noble"
server_machine="tf-landscape-server-noble"
client_name="profiling-client"
server_ip=$(lxc list ${server_machine} -c 4 | grep eth0 | awk '{print $2}')
server_hostname="${server_machine}.lxd"

profiling_time=7200

lxc exec ${client_machine} -- sudo bash -c "echo ${server_ip} ${server_hostname} >> /etc/hosts"

# SSL handshake
lxc exec ${client_machine} -- bash -c \
    "echo | openssl s_client -connect ${server_hostname}:443 | openssl x509 | sudo tee /etc/landscape/server.pem"

# Register client with server
lxc exec ${client_machine} -- sudo landscape-config --silent \
    --account-name="standalone" \
    --computer-title="${client_name}" \
    --registration-key="landscape" \
    --ping-url="http://${server_hostname}/ping" \
    --url="https://${server_hostname}/message-system" \
    --ssl-public-key="/etc/landscape/server.pem" \
    --ping-interval=10 \
    --exchange-interval=10 \
    --urgent-exchange-interval=10 \
    --log-level="debug"

# Profile on client
echo "Starting CPU profiling for ${profiling_time} seconds..."


for i in $(seq 1 ${profiling_time})
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
            WHERE computer_id=1
        \" | head -n 3 | tail -n 1 | sed 's/|/,/g' | sed 's/ //g' >> /home/ubuntu/package_counts.log
    "

    sleep 1
done

# Pull results
lxc file pull ${client_machine}/home/ubuntu/cpu_usage.log ./cpu_usage_$(date | sed 's/ /_/g').log
lxc file pull ${client_machine}/home/ubuntu/db_size.log ./db_size_$(date | sed 's/ /_/g').log  
lxc file pull ${server_machine}/home/ubuntu/package_counts.log ./package_counts_$(date | sed 's/ /_/g').log