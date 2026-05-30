output "subnet_id" {
  description = "OCID of the public subnet the host attaches to."
  value       = oci_core_subnet.public.id
}

output "nsg_id" {
  description = "OCID of the host network security group."
  value       = oci_core_network_security_group.host.id
}
