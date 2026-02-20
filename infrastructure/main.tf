provider "aws" {
  region = var.aws_region
}

resource "aws_vpc" "saas_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "SaaS-Platform-VPC"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.saas_vpc.id

  tags = {
    Name = "SaaS-Platform-IGW"
  }
}

resource "aws_subnet" "public_subnet" {
  vpc_id                  = aws_vpc.saas_vpc.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "${var.aws_region}a"

  tags = {
    Name = "SaaS-Platform-Public-Subnet"
  }
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.saas_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "SaaS-Platform-Public-RT"
  }
}

resource "aws_route_table_association" "public_rt_assoc" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_security_group" "saas_sg" {
  name        = "saas_platform_sg"
  description = "Allow HTTP, HTTPS, SSH, and API inbound traffic"
  vpc_id      = aws_vpc.saas_vpc.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "FastAPI Provisioning API (direct access, fallback when Traefik is misconfigured)"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Super Admin Dashboard (direct access)"
    from_port   = 8081
    to_port     = 8081
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "SaaS-Platform-SG"
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"] # Canonical
}

resource "aws_instance" "saas_server" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  key_name      = var.key_name

  subnet_id                   = aws_subnet.public_subnet.id
  vpc_security_group_ids      = [aws_security_group.saas_sg.id]
  associate_public_ip_address = true

  # Fix: Use templatefile() to inject variables instead of hardcoding secrets in user_data.sh
  user_data = templatefile("${path.module}/user_data.sh", {
    db_password = var.db_password
    domain_name = var.domain_name
  })

  tags = {
    Name = "SaaS-Platform-Server"
  }

  root_block_device {
    volume_size = 50 # GB — needed for Docker images and database data
    volume_type = "gp3"
  }
}
