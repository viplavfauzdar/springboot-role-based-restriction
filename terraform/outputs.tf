output "ecr_repository_url" {
  value       = aws_ecr_repository.app.repository_url
  description = "ECR repo URL to push images to"
}

output "instance_public_ip" {
  value       = aws_instance.app.public_ip
  description = "EC2 public IP"
}

output "app_url" {
  value       = "http://${aws_instance.app.public_ip}"
  description = "HTTP endpoint for your app"
}