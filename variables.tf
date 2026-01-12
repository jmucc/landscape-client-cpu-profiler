variable "landscape_server_image" {
  type        = string
  description = "Name of the LXD container image to use for the server instance"
}

variable "landscape_client_image" {
  type        = string
  description = "Name of the LXD image to use for the client instance"
}

variable "server_certificate_hostname" {
  type        = string
  description = "Hostname on the certificate in the Landscape server image."
}

variable "pro_token" {
  type        = string
  description = "Optionally, a pro token to attach to the client."
  default     = ""
}
