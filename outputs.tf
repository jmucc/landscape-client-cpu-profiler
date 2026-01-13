output "server_lxd_instance_name" {
  description = "Name of the LXD server instance"
  value       = lxd_instance.server.name
}

output "client_lxd_instance_name" {
  description = "Name of the LXD client instance"
  value       = lxd_instance.client.name
}

output "server_certificate_hostname" {
  description = "Hostname on the certificate in the Landscape server image."
  value       = var.server_certificate_hostname
}

output "pro_token" {
  description = "If provided, a pro token to attach to the client."
  value       = var.pro_token
}

output "server_ipv4_address" {
  description = "IPv4 address of the server"
  value       = lxd_instance.server.ipv4_address
}

output "client_ipv4_address" {
  description = "IPv4 address of the client"
  value       = lxd_instance.client.ipv4_address
}

output "server_lxd_image" {
  description = "LXD image used for the server instance"
  value       = var.landscape_server_image
}

output "client_lxd_image" {
  description = "LXD image used for the client instance"
  value       = var.landscape_client_image
}
