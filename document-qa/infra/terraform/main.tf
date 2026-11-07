provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "document-qa"
      Environment = "lab"
      ManagedBy   = "terraform"
    }
  }
}

# Read ONLY: these resources already exist and are owned outside this stack.
# No aws_vpc, aws_subnet, aws_route_table, or aws_internet_gateway resources!
data "aws_vpc" "existing" {
  id = var.vpc_id
}

data "aws_subnet" "existing" {
  id = var.subnet_id
}

# Canonical Ubuntu 24.04 LTS ARM64 AMI, from the AWS public parameter.
data "aws_ssm_parameter" "ubuntu_arm64" {
  name = "/aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id"
}

# NEW isolated SG, attached only to this lab's EC2. Never reuse an existing SG.
resource "aws_security_group" "k3s" {
  name_prefix = "document-qa-k3s-"
  description = "Document QA K3s lab: no inbound traffic, outbound HTTPS/registry access"
  vpc_id      = data.aws_vpc.existing.id

  # No ingress rules. Access to the instance is by outbound SSM session.
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Outbound SSM, K3s installer, image pulls and Cloudflare Tunnel"
  }

  tags = { Name = "document-qa-k3s" }
}

resource "aws_iam_role" "ssm" {
  name_prefix = "document-qa-ssm-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ssm.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "k3s" {
  name_prefix = "document-qa-k3s-"
  role        = aws_iam_role.ssm.name
}

resource "aws_instance" "k3s" {
  ami                         = data.aws_ssm_parameter.ubuntu_arm64.value
  instance_type               = var.instance_type
  subnet_id                   = data.aws_subnet.existing.id
  vpc_security_group_ids      = [aws_security_group.k3s.id]
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.k3s.name

  credit_specification {
    cpu_credits = "standard"
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 30
    encrypted             = true
    delete_on_termination = true
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    k3s_version = var.k3s_version
  })
  user_data_replace_on_change = true

  tags = { Name = "document-qa-k3s-graviton" }

  lifecycle {
    precondition {
      condition     = data.aws_subnet.existing.vpc_id == data.aws_vpc.existing.id
      error_message = "Selected subnet_id is not in the selected vpc_id."
    }
  }

  depends_on = [aws_iam_role_policy_attachment.ssm]
}
