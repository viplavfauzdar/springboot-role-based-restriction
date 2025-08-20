# Terraform input variables

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

# Instance type for EC2. Use Arm64 Graviton (cheap): t4g.small (your choice)
# For x86 fallback, you can use t3.micro.
variable "instance_type" {
  type    = string
  default = "t4g.small"
}

# Name to register the SSH key pair as in AWS (e.g., "springboot-key")
variable "key_name" {
  type = string
}

# Your *public* key contents (the line from ~/.ssh/id_ed25519.pub)
variable "ssh_public_key" {
  type = string
}

# CIDR allowed to reach the instance on exposed ports; lock down later
variable "allowed_cidr" {
  type    = string
  default = "0.0.0.0/0"
}

# Container image to run on the instance
variable "docker_image" {
  type    = string
  default = "ghcr.io/viplavfauzdar/springboot-role-based-restriction:latest"
}

# Spring Boot container port (internal)
variable "container_port" {
  type    = number
  default = 8080
}

# Public host port to expose (external)
variable "host_port" {
  type    = number
  default = 80
}