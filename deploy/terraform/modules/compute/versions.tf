terraform {
  required_version = ">= 1.6"
  required_providers {
    # Map the `oci` provider to the oracle namespace inside the module, else
    # Terraform would assume hashicorp/oci. Provider config is inherited from root.
    oci = {
      source = "oracle/oci"
    }
  }
}
