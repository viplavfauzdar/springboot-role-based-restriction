output "instance_ip" {
  value = aws_instance.springboot_app.public_ip
}
