resource "oci_core_vcn" "range" {
  compartment_id = var.compartment_ocid
  cidr_blocks    = ["10.0.0.0/16"]
  display_name   = "range-vcn"
  dns_label      = "range"
  freeform_tags  = var.common_tags
}

resource "oci_core_internet_gateway" "range" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.range.id
  display_name   = "range-igw"
  freeform_tags  = var.common_tags
}

resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.range.id
  display_name   = "range-rt-public"
  freeform_tags  = var.common_tags

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.range.id
  }
}

resource "oci_core_subnet" "public" {
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_vcn.range.id
  cidr_block        = "10.0.1.0/24"
  display_name      = "range-subnet-public"
  dns_label         = "public"
  route_table_id    = oci_core_route_table.public.id
  security_list_ids = [oci_core_vcn.range.default_security_list_id]
  freeform_tags     = var.common_tags
}

# NSG (preferred over security lists): a tight allow-list. Everything not matched
# below is denied — NSGs have no implicit allow-all.
resource "oci_core_network_security_group" "host" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.range.id
  display_name   = "range-nsg-host"
  freeform_tags  = var.common_tags
}

# Ingress: SSH only, from the operator CIDR. The API/UI stay closed — reach them
# over an SSH tunnel or Tailscale, never by opening a port here.
resource "oci_core_network_security_group_security_rule" "ssh_in" {
  network_security_group_id = oci_core_network_security_group.host.id
  direction                 = "INGRESS"
  protocol                  = "6" # TCP
  source                    = var.allowed_ssh_cidr
  source_type               = "CIDR_BLOCK"
  description               = "SSH from operator"

  tcp_options {
    destination_port_range {
      min = 22
      max = 22
    }
  }
}

# Egress: HTTP (80) for the OCI Ubuntu apt mirrors, HTTPS (443) for Docker/gVisor/
# uv repos + model APIs, and DNS (53). Port 80 is needed because the base Ubuntu
# archive is http — without it cloud-init's apt step fails (see ADR 0004). Range
# *container* egress is denied separately, in-Docker, by step 2.3.
resource "oci_core_network_security_group_security_rule" "http_out" {
  network_security_group_id = oci_core_network_security_group.host.id
  direction                 = "EGRESS"
  protocol                  = "6" # TCP
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
  description               = "HTTP egress (Ubuntu apt mirrors)"

  tcp_options {
    destination_port_range {
      min = 80
      max = 80
    }
  }
}

resource "oci_core_network_security_group_security_rule" "https_out" {
  network_security_group_id = oci_core_network_security_group.host.id
  direction                 = "EGRESS"
  protocol                  = "6" # TCP
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
  description               = "HTTPS egress (registries, model APIs)"

  tcp_options {
    destination_port_range {
      min = 443
      max = 443
    }
  }
}

resource "oci_core_network_security_group_security_rule" "dns_udp_out" {
  network_security_group_id = oci_core_network_security_group.host.id
  direction                 = "EGRESS"
  protocol                  = "17" # UDP
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
  description               = "DNS egress (UDP)"

  udp_options {
    destination_port_range {
      min = 53
      max = 53
    }
  }
}

resource "oci_core_network_security_group_security_rule" "dns_tcp_out" {
  network_security_group_id = oci_core_network_security_group.host.id
  direction                 = "EGRESS"
  protocol                  = "6" # TCP
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
  description               = "DNS egress (TCP)"

  tcp_options {
    destination_port_range {
      min = 53
      max = 53
    }
  }
}
