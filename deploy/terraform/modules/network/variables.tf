variable "compartment_ocid" {
  description = "OCID of the compartment that owns the network resources."
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to reach SSH (22)."
  type        = string
}

variable "common_tags" {
  description = "Freeform tags applied to every resource."
  type        = map(string)
}
