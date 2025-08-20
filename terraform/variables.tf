variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "ECR repo and app name"
  type        = string
  default     = "springboot-app"
}

variable "image_tag" {
  description = "Docker image tag to deploy (e.g., latest or a Git SHA)"
  type        = string
  default     = "latest"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro" # free-tier eligible in many regions
}

variable "ssh_key_name" {
  description = "Optional EC2 key pair name to allow SSH"
  type        = string
  default     = null
}