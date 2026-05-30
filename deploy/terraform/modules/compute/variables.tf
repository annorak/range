variable "compartment_ocid" {
  description = "OCID of the compartment that owns the compute resources."
  type        = string
}

variable "tenancy_ocid" {
  description = "Tenancy OCID (used to enumerate availability domains)."
  type        = string
}

variable "instance_shape" {
  description = "Compute shape (x86 AMD flex)."
  type        = string
}

variable "instance_ocpus" {
  description = "OCPUs for the flex shape."
  type        = number
}

variable "instance_memory_gb" {
  description = "Memory (GB) for the flex shape."
  type        = number
}

variable "ssh_public_key" {
  description = "Operator SSH public key, injected as the ubuntu user's authorized key."
  type        = string
}

variable "os_image_ocid" {
  description = "Pin a specific OS image OCID; empty looks up the latest Ubuntu 24.04 x86_64."
  type        = string
}

variable "block_volume_gb" {
  description = "Size of the /data block volume (Docker layers + trace state)."
  type        = number
}

variable "tailscale_auth_key" {
  description = "Optional Tailscale auth key; empty skips Tailscale install."
  type        = string
  sensitive   = true
}

variable "subnet_id" {
  description = "OCID of the subnet to attach the host VNIC to."
  type        = string
}

variable "nsg_id" {
  description = "OCID of the network security group to apply to the host VNIC."
  type        = string
}

variable "common_tags" {
  description = "Freeform tags applied to every resource."
  type        = map(string)
}
