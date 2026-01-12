resource lxd_instance server {
    name = "profiling-landscape-server"
    image = var.landscape_server_image
}

resource lxd_instance client {
    name = "profiling-landscape-client"
    image = var.landscape_client_image
    # type = "virtual-machine"
}