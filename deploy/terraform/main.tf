# Root module: composes the network + compute child modules. Provider config and
# input variables live alongside this file; each resource set is its own module.
locals {
  common_tags = {
    project    = "range"
    env        = var.env
    managed_by = "terraform"
  }
}

module "network" {
  source           = "./modules/network"
  compartment_ocid = var.compartment_ocid
  allowed_ssh_cidr = var.allowed_ssh_cidr
  common_tags      = local.common_tags
}

module "compute" {
  source             = "./modules/compute"
  compartment_ocid   = var.compartment_ocid
  tenancy_ocid       = var.tenancy_ocid
  instance_shape     = var.instance_shape
  instance_ocpus     = var.instance_ocpus
  instance_memory_gb = var.instance_memory_gb
  ssh_public_key     = var.ssh_public_key
  os_image_ocid      = var.os_image_ocid
  block_volume_gb    = var.block_volume_gb
  tailscale_auth_key = var.tailscale_auth_key
  subnet_id          = module.network.subnet_id
  nsg_id             = module.network.nsg_id
  common_tags        = local.common_tags
}
