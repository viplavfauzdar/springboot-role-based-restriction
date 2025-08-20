# Use the default VPC and its first public subnet to keep costs minimal.
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_key_pair" "deployer" {
  key_name   = var.key_name
  public_key = var.ssh_public_key
}

resource "aws_security_group" "app_sg" {
  name        = "springboot-minimal-sg"
  description = "Allow SSH and HTTP"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  ingress {
    description = "HTTP"
    from_port   = var.host_port
    to_port     = var.host_port
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Amazon Linux 2023 ARM (for t4g). If you use t3.micro, switch to x86_64 AMI.
data "aws_ami" "al2023_arm" {
  most_recent = true
  owners      = ["137112412989"] # Amazon

  filter {
    name   = "name"
    values = ["al2023-ami-*-kernel-6.1-arm64"]
  }
}

# Simple user_data: install Docker and run your container (pulling from GHCR).
locals {
  user_data = <<-BASH
    #!/bin/bash
    set -eux
    dnf update -y
    dnf install -y docker
    systemctl enable --now docker
    usermod -aG docker ec2-user || true

    # login to ghcr only if private; public needs no auth
    # docker login ghcr.io -u USERNAME -p $${GITHUB_TOKEN}

    # stop old
    docker rm -f app || true

    # run latest from GHCR
    docker run -d --name app --restart=always \
      -p ${var.host_port}:${var.container_port} \
      ${var.docker_image}
  BASH
}

resource "aws_instance" "app" {
  ami                         = data.aws_ami.al2023_arm.id
  instance_type               = var.instance_type
  subnet_id                   = data.aws_subnets.public.ids[0]
  vpc_security_group_ids      = [aws_security_group.app_sg.id]
  associate_public_ip_address = true
  key_name                    = aws_key_pair.deployer.key_name
  user_data                   = local.user_data

  tags = { Name = "springboot-minimal" }
}

output "public_ip"   { value = aws_instance.app.public_ip }
output "public_dns"  { value = aws_instance.app.public_dns }