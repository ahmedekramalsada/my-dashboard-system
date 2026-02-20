variable "aws_region" {
  description = "AWS region"
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 Instance Type"
  default     = "t3.medium" # Minimum recommended for running multiple Docker containers
}

variable "key_name" {
  description = "Name of the existing EC2 KeyPair to enable SSH access to the instance"
  type        = string
}

variable "domain_name" {
  description = "Base domain name for Traefik routing and tenant stores (e.g. example.com)"
  type        = string
  default     = "example.com"
}

variable "db_password" {
  description = "Root password for the shared PostgreSQL instance. Inject from pipeline secrets — never hardcode."
  type        = string
  sensitive   = true
}
