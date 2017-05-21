
variable "resource_suffix" {}
variable "public_key_path" {}
variable "private_key_path" {}
variable "flavor" {}
variable "image" {}
variable "tests_pattern" {}

output "router_name" { value = "${openstack_networking_router_v2.router.name}" }
output "router_id" { value = "${openstack_networking_router_v2.router.id}" }
output "network_name" { value = "${openstack_networking_network_v2.network.name}" }
output "network_id" { value = "${openstack_networking_network_v2.network.id}" }
output "subnet_name" { value = "${openstack_networking_subnet_v2.subnet.name}" }
output "subnet_id" { value = "${openstack_networking_subnet_v2.subnet.id}" }
output "security_group_name" { value = "${openstack_compute_secgroup_v2.security_group.name}" }
output "security_group_id" { value = "${openstack_compute_secgroup_v2.security_group.id}" }
output "keypair_name" { value = "${openstack_compute_keypair_v2.keypair.name}" }
{% for server in servers %}
output "public_ip_address_{{ loop.index0 }}" { value = "${openstack_networking_floatingip_v2.floatingip{{ loop.index0 }}.address}" }
# output "private_ip_address_{{ loop.index0 }}" { value = "${openstack_compute_instance_v2.server{{ loop.index0 }}.network.0.fixed_ip_v4}" }
# output "server_name_{{ loop.index0 }}" { value = "${openstack_compute_instance_v2.server{{ loop.index0 }}.name}" }
# output "server_id_{{ loop.index0 }}" { value = "${openstack_compute_instance_v2.server{{ loop.index0 }}.id}" }
{% endfor %}


resource "openstack_networking_router_v2" "router" {
  name = "router-${var.resource_suffix}"
  external_gateway = "dda079ce-12cf-4309-879a-8e67aec94de4"
}

resource "openstack_networking_network_v2" "network" {
  name = "network-${var.resource_suffix}"
}

resource "openstack_networking_subnet_v2" "subnet" {
  name = "subnet-${var.resource_suffix}"
  network_id = "${openstack_networking_network_v2.network.id}"
  cidr = "10.0.0.0/24"
  dns_nameservers = ["8.8.8.8", "8.8.4.4"]
}

resource "openstack_networking_router_interface_v2" "router_interface" {
  router_id = "${openstack_networking_router_v2.router.id}"
  subnet_id = "${openstack_networking_subnet_v2.subnet.id}"
}

resource "openstack_compute_secgroup_v2" "security_group" {
  name = "security_group-${var.resource_suffix}"
  description = "cloudify manager security group"
  rule {
    from_port = 22
    to_port = 22
    ip_protocol = "tcp"
    cidr = "0.0.0.0/0"
  }
  rule {
    from_port = 80
    to_port = 80
    ip_protocol = "tcp"
    cidr = "0.0.0.0/0"
  }
  rule {
    from_port = 8086
    to_port = 8086
    ip_protocol = "tcp"
    cidr = "0.0.0.0/0"
  }
  rule {
    from_port = 8080
    to_port = 8080
    ip_protocol = "tcp"
    cidr = "0.0.0.0/0"
  }
  rule {
    from_port = 1 
    to_port = 65535
    ip_protocol = "tcp"
    cidr = "${openstack_networking_subnet_v2.subnet.cidr}"
  }
}

resource "openstack_compute_keypair_v2" "keypair" {
  name = "keypair-${var.resource_suffix}"
  public_key = "${file("${var.public_key_path}")}"
}


{% for server in servers %}

resource "openstack_networking_floatingip_v2" "floatingip{{ loop.index0 }}" {
  pool = "GATEWAY_NET"
}

# resource "openstack_compute_floatingip_associate_v2" "fip_associate{{ loop.index0 }}" {
#   floating_ip = "${openstack_networking_floatingip_v2.floatingip{{ loop.index0 }}.address}"
#   instance_id = "${openstack_compute_instance_v2.server{{ loop.index0 }}.id}"
# }

resource "openstack_compute_instance_v2" "server{{ loop.index0 }}" {
  name = "server-{{ loop.index0 }}-${var.resource_suffix}"
  image_name = "${var.image}"
  flavor_name = "${var.flavor}"
  key_pair = "${openstack_compute_keypair_v2.keypair.name}"
  security_groups = ["${openstack_compute_secgroup_v2.security_group.name}"]
  network {
    uuid = "${openstack_networking_network_v2.network.id}"
  }
  floating_ip = "${openstack_networking_floatingip_v2.floatingip{{ loop.index0 }}.address}"

  connection {
    type = "ssh"
    user = "centos"
    private_key = "${file("${var.private_key_path}")}"
    timeout = "10m"
  }

  provisioner "file" {
    source = "resources/config.json"
    destination = "/tmp/config.json"
  }

  provisioner "file" {
    source = "resources/prepare-env.sh"
    destination = "/tmp/prepare-env.sh"
  }

  # this file is created by the program which invokes terraform
  provisioner "file" {
    source = "cloudify-premium.tar.gz"
    destination = "/tmp/cloudify-premium.tar.gz"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/prepare-env.sh",
      "/tmp/prepare-env.sh"
    ]
  }

  provisioner "file" {
    source = "resources/run-tests.py"
    destination = "/tmp/run-tests.py"
  }

  provisioner "file" {
    source = "resources/weights.json"
    destination = "/tmp/weights.json"
  }


  provisioner "remote-exec" {
    inline = [
      "source venv/bin/activate",
      "python /tmp/run-tests.py --repos ~/repos --group-number {{ loop.index }} --number-of-groups {{ servers|length }} --pattern ${var.tests_pattern} --weights-file /tmp/weights.json --config-file /tmp/config.json"
    ]
    on_failure = "continue"
  }

  provisioner "remote-exec" {
    inline = [
      "tar czf report-{{ loop.index }}.tar.gz *.xml",
      "nohup python -m SimpleHTTPServer 8080 > output.txt 2>&1 &",
      "sleep 3"
    ]
  }

  provisioner "local-exec" {
    command = "curl -O http://${openstack_networking_floatingip_v2.floatingip{{ loop.index0 }}.address}:8080/report-{{ loop.index }}.tar.gz"
  }

  provisioner "local-exec" {
    command = "tar xzvf report-{{ loop.index }}.tar.gz"
  }

}

{% endfor %}
