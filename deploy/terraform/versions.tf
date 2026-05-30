terraform {
  required_version = ">= 1.6"
  required_providers {
    # The official OCI provider is published under the `oracle` namespace on the
    # Terraform Registry (there is no `hashicorp/oci`); see ADR 0004.
    oci = {
      source  = "oracle/oci"
      version = "~> 6.0"
    }
  }
}

provider "oci" {
  # Auth comes from the operator's ~/.oci/config (API-key); only the region is
  # parameterized so the same module runs against any region.
  region = var.region
}
