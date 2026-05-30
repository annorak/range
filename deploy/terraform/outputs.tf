output "instance_public_ip" {
  description = "Public IP of the range host."
  value       = module.compute.instance_public_ip
}

output "instance_id" {
  description = "OCID of the range host instance."
  value       = module.compute.instance_id
}

output "ssh_command" {
  description = "Ready-to-run SSH command for the operator."
  value       = "ssh ubuntu@${module.compute.instance_public_ip}"
}
