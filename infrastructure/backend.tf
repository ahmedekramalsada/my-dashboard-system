terraform {
  backend "s3" {
    bucket  = "my-dashboard-s3"
    key     = "infrastructure/terraform.tfstate"
    region  = "us-east-1" # Update this to your desired AWS region
    encrypt = true
    # dynamodb_table = "terraform-state-lock" # Highly recommended for state locking in a team
  }
}
