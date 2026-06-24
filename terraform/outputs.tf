output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.api.id
}

output "public_ip" {
  description = "Public IP of the API server"
  value       = aws_instance.api.public_ip
}

output "public_dns" {
  description = "Public DNS of the API server"
  value       = aws_instance.api.public_dns
}

output "ssh_command" {
  description = "SSH into the server"
  value       = "ssh -i ~/.ssh/ra-deploy ec2-user@${aws_instance.api.public_ip}"
}

output "api_url" {
  description = "API health check URL"
  value       = "http://${aws_instance.api.public_ip}:8000/health"
}
