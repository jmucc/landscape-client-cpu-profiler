output "server_name" {
  description = "Name of the LXD server instance"
  value       = lxd_instance.server.name
}

output "client_name" {
  description = "Name of the LXD client instance"
  value       = lxd_instance.client.name
}

output "server_image" {
  description = "Image used for the server"
  value       = var.landscape_server_image
}

output "client_image" {
  description = "Image used for the client"
  value       = var.landscape_client_image
}

output "server_ipv4_address" {
  description = "IPv4 address of the server"
  value       = lxd_instance.server.ipv4_address
}

output "client_ipv4_address" {
  description = "IPv4 address of the client"
  value       = lxd_instance.client.ipv4_address
}
