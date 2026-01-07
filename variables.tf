variable "pro_token" {
    type        = string
    sensitive   = true
}

variable "landscape_client_package" {
    type        = string
    default     = "landscape-client"
}

variable "client-ppa" {
    type        = string
    default     = null
}

variable "server-ppa" {
    type        = string
    default     = "ppa:landscape/self-hosted-beta"
}

