variable "cluster_name" { type = string }
variable "region"       { type = string }
variable "node_count"   { type = number }
variable "node_size"    { type = string }
variable "k8s_version"  { type = string }
variable "tags"         { type = map(string) }

# VPC for the EKS cluster
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.cluster_name}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.region}a", "${var.region}b", "${var.region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }

  tags = var.tags
}

# EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = var.k8s_version

  vpc_id                         = module.vpc.vpc_id
  subnet_ids                     = module.vpc.private_subnets
  cluster_endpoint_public_access = true

  eks_managed_node_groups = {
    default = {
      min_size       = 1
      max_size       = var.node_count + 2
      desired_size   = var.node_count
      instance_types = [var.node_size]
      capacity_type  = "ON_DEMAND"
    }
  }

  tags = var.tags
}

output "cluster_endpoint"            { value = module.eks.cluster_endpoint }
output "cluster_certificate_authority" { value = module.eks.cluster_certificate_authority_data }
output "cluster_name"                { value = module.eks.cluster_name }
