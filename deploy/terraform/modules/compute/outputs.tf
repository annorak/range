output "instance_public_ip" {
  description = "Public IP of the range host."
  value       = oci_core_instance.host.public_ip
}

output "instance_id" {
  description = "OCID of the range host instance."
  value       = oci_core_instance.host.id
}
