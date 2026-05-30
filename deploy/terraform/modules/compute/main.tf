data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

# Latest Canonical Ubuntu 24.04 x86_64 image — only queried when the operator
# hasn't pinned an explicit image OCID.
data "oci_core_images" "ubuntu" {
  count                    = var.os_image_ocid == "" ? 1 : 0
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "24.04"
  shape                    = var.instance_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

locals {
  image_id = var.os_image_ocid != "" ? var.os_image_ocid : data.oci_core_images.ubuntu[0].images[0].id
}

resource "oci_core_instance" "host" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = var.compartment_ocid
  display_name        = "range-host"
  shape               = var.instance_shape
  freeform_tags       = var.common_tags

  shape_config {
    ocpus         = var.instance_ocpus
    memory_in_gbs = var.instance_memory_gb
  }

  source_details {
    source_type = "image"
    source_id   = local.image_id
  }

  create_vnic_details {
    subnet_id        = var.subnet_id
    nsg_ids          = [var.nsg_id]
    assign_public_ip = true
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    # templatefile (not file) so the optional Tailscale key reaches cloud-init.
    user_data = base64encode(templatefile("${path.module}/cloud-init/bootstrap.yaml", {
      tailscale_auth_key = var.tailscale_auth_key
    }))
  }
}

# Block volume for Docker layers + trace/state, so they survive instance
# recreation. cloud-init formats (if new) and mounts it at /data.
resource "oci_core_volume" "data" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = var.compartment_ocid
  display_name        = "range-data"
  size_in_gbs         = var.block_volume_gb
  freeform_tags       = var.common_tags
}

resource "oci_core_volume_attachment" "data" {
  attachment_type = "paravirtualized"
  instance_id     = oci_core_instance.host.id
  volume_id       = oci_core_volume.data.id
}
