variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type (free tier eligible)"
  type        = string
  default     = "t2.micro"
}

variable "ami_id" {
  description = "Amazon Linux 2023 AMI ID (us-east-1)"
  type        = string
  default     = "ami-0c02fb55956c7d316"
}

variable "ssh_public_key" {
  description = "SSH public key for EC2 access"
  type        = string
}
