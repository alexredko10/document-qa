variable "aws_region" {
  description = "London. The selected existing VPC and subnet must be in this region."
  type        = string
  default     = "eu-west-2"
}

variable "vpc_id" {
  description = "Existing VPC to READ (not manage); e.g. vpc-..."
  type        = string

  validation {
    condition     = can(regex("^vpc-[a-f0-9]+$", var.vpc_id))
    error_message = "vpc_id must be a valid VPC ID."
  }
}

variable "subnet_id" {
  description = "Existing public subnet with outbound route via IGW; e.g. subnet-..."
  type        = string

  validation {
    condition     = can(regex("^subnet-[a-f0-9]+$", var.subnet_id))
    error_message = "subnet_id must be a valid subnet ID."
  }
}

variable "instance_type" {
  description = "ARM64 Graviton instance, 8 GiB memory for K3s + Argo CD."
  type        = string
  default     = "t4g.large"

  validation {
    condition     = startswith(var.instance_type, "t4g.")
    error_message = "Use a Graviton T4g instance type for this lab."
  }
}

variable "k3s_version" {
  description = "Pinned K3s release; changing user data replaces the instance."
  type        = string
  default     = "v1.35.5+k3s1"
}
