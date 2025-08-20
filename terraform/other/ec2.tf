resource "aws_instance" "springboot_app" {
  ami           = "ami-0c55b159cbfafe1f0" # Amazon Linux 2 AMI (example)
  instance_type = "t2.micro"
  subnet_id     = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.app_sg.id]

  user_data = <<-EOF
              #!/bin/bash
              yum update -y
              amazon-linux-extras install docker -y
              service docker start
              docker run -d -p 8080:8080 viplavfauzdar/springboot-role-based-restriction:latest
              EOF

  tags = {
    Name = "SpringBootApp"
  }
}
