# Document QA — Graviton + K3s in an EXISTING London VPC

**Safety principle:** this Terraform stack only *reads* the existing VPC and subnet via data sources. It creates and can destroy **only** the new Document QA security group, IAM role/policy attachment, instance profile, EC2 instance and its root EBS volume. It does NOT create, import, modify, or destroy VPCs, subnets, route tables, Internet Gateways or NAT Gateways.

The project uses `eu-west-2` (London), EC2 `t4g.large`, Ubuntu 24.04 ARM64, encrypted 30 GiB gp3, IMDSv2, SSM access and a single-node K3s lab. The SG has **zero inbound rules**. GitHub Actions needs no AWS credentials.

## 0. Very important if you already used the previous ZIP

Before replacing an existing Terraform configuration, run `terraform state list` in the same directory (after `terraform init` if needed). If it lists **any** `aws_vpc.*`, `aws_subnet.*`, `aws_route_table.*`, `aws_route_table_association.*`, or `aws_internet_gateway.*` resources, **STOP**. The previous configuration may have provisioned network resources in this Terraform state. Simply deleting those resource blocks from the configuration would plan to **destroy those resources**. Migrating that state requires a separate controlled procedure. Never apply or destroy in that situation without reviewing it.

## 1. Find an existing suitable subnet (read-only AWS CLI)

Use the AWS account/profile that owns the network:

```sh
export AWS_REGION=eu-west-2
aws sts get-caller-identity
aws ec2 describe-vpcs --region "$AWS_REGION" \
  --query 'Vpcs[].{VpcId:VpcId,CIDR:CidrBlock,Name:Tags[?Key==`Name`]|[0].Value}' --output table
```

For this lab we verified VPC `vpc-0167fe5dbd3c2c1e3`. Choose the intended VPC and set `VPC_ID=vpc-...` if using another network. List its subnets:

```sh
aws ec2 describe-subnets --region "$AWS_REGION" \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[].{SubnetId:SubnetId,AZ:AvailabilityZone,AutoPublicIP:MapPublicIpOnLaunch,Name:Tags[?Key==`Name`]|[0].Value}' --output table
```

**We verified** subnet `subnet-0ed531b8362c2d71e` (eu-west-2a) is explicitly associated with route table `rtb-09ebcd32bb889ea6f`, with a default route via IGW `igw-040b4349d13ab6a3c`. **Choose an existing public subnet** with an IPv4 default route `0.0.0.0/0 -> igw-...`. Verify route tables in that VPC (be careful: a subnet may inherit the *main* route table):

```sh
aws ec2 describe-route-tables --region "$AWS_REGION" \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'RouteTables[].{Table:RouteTableId,Associations:Associations[].{Subnet:SubnetId,Main:Main},DefaultRoutes:Routes[?DestinationCidrBlock==`0.0.0.0/0`].{IGW:GatewayId,NAT:NatGatewayId}}' \
  --output json
```

This lab explicitly assigns a public IPv4 address to the EC2 instance but **does not allow any inbound SG traffic**. The public IPv4 is necessary for internet egress via IGW. If you need a private subnet, that is a different deployment: you must already have NAT/internet egress or arrange SSM VPC endpoints, plus outbound access to K3s installation, GHCR, and Cloudflare. We deliberately don't modify the existing routing.

## 2. Configure and review Terraform

```sh
cd document-qa/infra/terraform
cp terraform.tfvars.example terraform.tfvars
# Prepopulated with the verified London VPC/subnet IDs. Double-check against your AWS account.
terraform init
terraform fmt -check
terraform validate
terraform state list
terraform plan -out=tfplan
terraform show -no-color tfplan
```

**Expected new managed resource addresses** are exactly:

```text
aws_security_group.k3s
aws_iam_role.ssm
aws_iam_role_policy_attachment.ssm
aws_iam_instance_profile.k3s
aws_instance.k3s
```

Plus read-only `data.aws_vpc.existing`, `data.aws_subnet.existing`, and `data.aws_ssm_parameter.ubuntu_arm64`. There must be **no `-/+`, `~`, or `-` operations affecting existing infrastructure**, and no `aws_vpc`, `aws_subnet`, `aws_route_table`, or `aws_internet_gateway` managed resources. Terraform will create an EBS root volume as part of EC2.

If this project has already initialized/applied Terraform, **do not reset or delete its state**. State is the safety boundary that distinguishes managed resources from data sources.

## 3. Provision and connect

Only after reviewing the plan:

```sh
terraform apply tfplan
terraform output ssm_command
```

On the EC2 via Session Manager (may need a few minutes to register):

```sh
sudo cloud-init status --wait
sudo systemctl is-active k3s
sudo k3s kubectl get nodes -o wide
sudo k3s kubectl get pods -A
```

SSM requires the EC2 role `AmazonSSMManagedInstanceCore`, a working SSM Agent, outbound HTTPS connectivity to AWS SSM endpoints, and permission for your AWS identity to start sessions. No SSH/22, K3s/6443 or Argo UI ingress is opened.

## 4. Tear down SAFELY

Run this **from this exact directory and state**:

```sh
terraform plan -destroy
terraform destroy
```

Review the destroy plan first: it should target only the lab resources above, **never pre-existing networking**. Terraform state is local and gitignored; keep it safely until the teardown. EC2, EBS, and public IPv4 incur charges while applicable. No NAT Gateway is created. K3s documents held in memory will be lost when EC2 stops/replaces.

`user_data_replace_on_change = true`: changes to cloud-init may replace the instance. Updating the 'current' AMI data parameter might also trigger replacement on a future plan. This is a learning environment, not a production HA deployment.
