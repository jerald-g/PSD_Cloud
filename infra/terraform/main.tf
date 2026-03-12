terraform {
  required_version = ">= 1.7.0"

  required_providers {
    # All providers are declared but only the selected cloud_provider module
    # will be activated via the count/for_each meta-argument pattern below.
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }

  # Remote state – configure for your cloud backend before running apply.
  # Example for AWS S3:
  # backend "s3" {
  #   bucket = "psd-cloud-tfstate"
  #   key    = "psd-cloud/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

# ─── Cloud Provider Selection ──────────────────────────────────────────────

locals {
  is_aws   = var.cloud_provider == "aws"
  is_azure = var.cloud_provider == "azure"
  is_gcp   = var.cloud_provider == "gcp"

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ─── AWS ──────────────────────────────────────────────────────────────────

provider "aws" {
  region = var.region
  # Credentials sourced from environment variables:
  # AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
}

module "aws_cluster" {
  count  = local.is_aws ? 1 : 0
  source = "./modules/kubernetes-cluster/aws"

  cluster_name   = "${var.project_name}-${var.environment}"
  region         = var.region
  node_count     = var.k8s_node_count
  node_size      = var.k8s_node_size
  k8s_version    = var.k8s_version
  tags           = local.common_tags
}

module "aws_database" {
  count  = local.is_aws ? 1 : 0
  source = "./modules/database/aws"

  identifier     = "${var.project_name}-${var.environment}-db"
  instance_class = var.db_instance_class
  storage_gb     = var.db_storage_gb
  db_name        = var.db_name
  username       = var.db_username
  password       = var.db_password
  tags           = local.common_tags
}

module "aws_storage" {
  count  = local.is_aws ? 1 : 0
  source = "./modules/storage/aws"

  bucket_name = var.reports_bucket_name
  tags        = local.common_tags
}

# ─── Azure ─────────────────────────────────────────────────────────────────

provider "azurerm" {
  features {}
  # Credentials sourced from environment variables:
  # ARM_CLIENT_ID, ARM_CLIENT_SECRET, ARM_TENANT_ID, ARM_SUBSCRIPTION_ID
}

module "azure_cluster" {
  count  = local.is_azure ? 1 : 0
  source = "./modules/kubernetes-cluster/azure"

  cluster_name = "${var.project_name}-${var.environment}"
  location     = var.region
  node_count   = var.k8s_node_count
  node_size    = var.k8s_node_size
  k8s_version  = var.k8s_version
  tags         = local.common_tags
}

module "azure_database" {
  count  = local.is_azure ? 1 : 0
  source = "./modules/database/azure"

  server_name = "${var.project_name}-${var.environment}-pg"
  location    = var.region
  db_name     = var.db_name
  username    = var.db_username
  password    = var.db_password
  sku_name    = var.db_instance_class
  tags        = local.common_tags
}

module "azure_storage" {
  count    = local.is_azure ? 1 : 0
  source   = "./modules/storage/azure"

  account_name    = replace("${var.project_name}${var.environment}sa", "-", "")
  container_name  = var.reports_bucket_name
  location        = var.region
  tags            = local.common_tags
}

# ─── GCP ───────────────────────────────────────────────────────────────────

provider "google" {
  project = var.project_name
  region  = var.region
  # Credentials sourced from GOOGLE_APPLICATION_CREDENTIALS environment variable
}

module "gcp_cluster" {
  count  = local.is_gcp ? 1 : 0
  source = "./modules/kubernetes-cluster/gcp"

  cluster_name = "${var.project_name}-${var.environment}"
  region       = var.region
  node_count   = var.k8s_node_count
  machine_type = var.k8s_node_size
  k8s_version  = var.k8s_version
}

module "gcp_database" {
  count  = local.is_gcp ? 1 : 0
  source = "./modules/database/gcp"

  instance_name = "${var.project_name}-${var.environment}-pg"
  region        = var.region
  db_name       = var.db_name
  username      = var.db_username
  password      = var.db_password
  tier          = var.db_instance_class
}

module "gcp_storage" {
  count    = local.is_gcp ? 1 : 0
  source   = "./modules/storage/gcp"

  bucket_name = var.reports_bucket_name
  location    = var.region
}

# ─── Helm Deployment (cloud-agnostic) ─────────────────────────────────────

# Kubernetes and Helm providers are configured after cluster creation.
# In practice, run a second apply pass or use a separate workspace/stage.

module "psd_helm_release" {
  source = "./modules/helm-release"

  depends_on = [
    module.aws_cluster,
    module.azure_cluster,
    module.gcp_cluster,
  ]

  chart_path    = "../../helm"
  release_name  = var.project_name
  namespace     = "psd-cloud"

  db_url          = "postgresql://..."   # Populated from database module output
  minio_endpoint  = "..."               # Populate from storage module output
  jwt_secret      = "change-me-in-prod"
}
