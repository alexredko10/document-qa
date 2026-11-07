output "region" {
  value = var.aws_region
}

output "existing_vpc_id" {
  description = "Read-only input: never created or destroyed by this stack."
  value       = data.aws_vpc.existing.id
}

output "existing_subnet_id" {
  description = "Read-only input: never created or destroyed by this stack."
  value       = data.aws_subnet.existing.id
}

output "instance_id" {
  value = aws_instance.k3s.id
}

output "public_ip" {
  description = "Used for OUTBOUND access; EC2 SG allows zero inbound traffic."
  value       = aws_instance.k3s.public_ip
}

output "ssm_command" {
  value = "aws ssm start-session --target ${aws_instance.k3s.id} --region ${var.aws_region}"
}
