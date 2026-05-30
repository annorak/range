variable "region" {
  description = "OCI region identifier, e.g. us-ashburn-1."
  type        = string
}

variable "compartment_ocid" {
  description = "OCID of the compartment that owns all resources in this module."
  type        = string
}

variable "tenancy_ocid" {
  description = "Tenancy OCID (used to enumerate availability domains)."
  type        = string
}

variable "instance_shape" {
  description = "Compute shape. x86 AMD flex so all standard x86 images/containers work."
  type        = string
  default     = "VM.Standard.E4.Flex"
}

variable "instance_ocpus" {
  description = "OCPUs for the flex shape."
  type        = number
  default     = 4
}

variable "instance_memory_gb" {
  description = "Memory (GB) for the flex shape."
  type        = number
  default     = 24
}

variable "ssh_public_key" {
  description = "Operator SSH public key, injected as the ubuntu user's authorized key."
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to reach SSH (22). Lock to your IP in terraform.tfvars."
  type        = string
  default     = "0.0.0.0/0"
}

variable "os_image_ocid" {
  description = "Pin a specific OS image OCID; empty looks up the latest Ubuntu 24.04 x86_64."
  type        = string
  default     = ""
}

variable "block_volume_gb" {
  description = "Size of the /data block volume (holds Docker layers + trace state)."
  type        = number
  default     = 100
}

variable "tailscale_auth_key" {
  description = "Optional Tailscale auth key; empty skips Tailscale install (default off)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "env" {
  description = "Deployment environment tag."
  type        = string
  default     = "dev"
}
