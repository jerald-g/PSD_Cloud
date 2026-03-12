variable "cluster_name" { type = string }
variable "location"     { type = string }
variable "node_count"   { type = number }
variable "node_size"    { type = string }
variable "k8s_version"  { type = string }
variable "tags"         { type = map(string) }

resource "azurerm_resource_group" "main" {
  name     = "${var.cluster_name}-rg"
  location = var.location
  tags     = var.tags
}

resource "azurerm_kubernetes_cluster" "main" {
  name                = var.cluster_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = var.cluster_name
  kubernetes_version  = var.k8s_version

  default_node_pool {
    name       = "default"
    node_count = var.node_count
    vm_size    = var.node_size
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

output "cluster_endpoint"   { value = azurerm_kubernetes_cluster.main.kube_config[0].host }
output "cluster_name"       { value = azurerm_kubernetes_cluster.main.name }
output "kube_config_raw"    { value = azurerm_kubernetes_cluster.main.kube_config_raw; sensitive = true }
