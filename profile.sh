if [ -z "${SERVER_CONTAINER_IMAGE_NAME}" ]; then
    echo "ERROR: SERVER_CONTAINER_IMAGE_NAME environment variable is not set."
    exit 1
fi

if [ -z "${REGISTRATION_KEY}" ]; then
    echo "ERROR: REGISTRATION_KEY environment variable is not set."
    exit 1
fi

profiling_iterations=${1:-7200}

terraform init
terraform apply -replace="lxd_instance.server" -replace="lxd_instance.client" -auto-approve
./get_data.sh $profiling_iterations