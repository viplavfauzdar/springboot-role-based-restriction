provider "aws" {
  region = "us-east-1"
}

resource "aws_ecr_repository" "springboot_repo" {
  name                 = "testns/testnm/springboot-role-based-restriction"
  image_tag_mutability = "MUTABLE"

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name        = "SpringBoot Role-Based Restriction"
    Environment = "Dev"
  }
}
