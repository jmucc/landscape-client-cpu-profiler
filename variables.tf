variable "landscape_server_image" {
    type        = string
    description = "Name of the LXD container image to use for the server instance"
}

variable "landscape_client_image" {
    type        = string
    description = "Name of the LXD image to use for the client instance"
}
