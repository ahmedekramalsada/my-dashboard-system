variable "aws_region" {
  description = "AWS region"
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 Instance Type"
  default     = "t3.medium" # Minimum recommended for multiple containers
}

variable "key_name" {
  description = "Name of the existing EC2 KeyPair to SSH into the instance"
  type        = string
}

variable "domain_name" {
  description = "Base domain name for Traefik and Stores"
  type        = string
  default     = "example.com"
}
