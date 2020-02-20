import time
import yaml
import traceback
import openstack

from common import get_dict_from_yaml, logger


def _get_resource_config(connection, config, instance_name):
    image_attr = config.get('image_name') or config.get('image_id')
    flavor_attr = config.get('flavor_name') or config.get('flavor_id')
    network_attr = config.get('network_name') or config.get('network_id')
    image = connection.compute.find_image(image_attr)
    flavor = connection.compute.find_flavor(flavor_attr)
    network = connection.network.find_network(network_attr)
    resource_config = {
        'name': instance_name,
        'image_id': image.id,
        'flavor_id': flavor.id,
        'networks': [{'uuid': network.id}],
        'key_name': config['key_name'],
    }
    return resource_config


def create_sec_group_and_open_all_ports(connection):
    sec_group = connection.network.create_security_group(
        name='cluster-sec-group')
    connection.network.create_security_group_rule(
        security_group_id=sec_group.id,
        direction='ingress',
        remote_ip_prefix='0.0.0.0/0',
        protocol='tcp',
        port_range_min='1',
        port_range_max='65535',
        ethertype='IPv4')
    connection.network.create_security_group_rule(
        security_group_id=sec_group.id,
        direction='ingress',
        remote_ip_prefix='0.0.0.0/0',
        protocol='icmp',
        ethertype='IPv4')
    return sec_group


def _get_private_ip(connection, server_id):
    tmp_server = connection.get_server(server_id, detailed=True)
    start_time = time.time()
    while tmp_server.private_v4 == '':
        tmp_server = connection.get_server(server_id, detailed=True)
        end_time = time.time()
        if (end_time-start_time) > 60 and tmp_server.private_v4 == '':
            raise Exception('Could not get the private ip of the server: {}'
                            .format(server_id))  # Timeout
    return tmp_server.private_v4


def _create_floating_ip(connection, config, resource_config):
    gateway_network = (config.get('gateway_network_name') or
                       config.get('gateway_net_id'))
    return connection.create_floating_ip(network=gateway_network,
                                         server=resource_config)


def _add_floating_ip_to_server(connection, server_id, floating_ip_address):
    connection.compute.add_floating_ip_to_server(server_id,
                                                 floating_ip_address)


def _create_server(connection, resource_config, sec_group_id):
    server = connection.compute.create_server(
        image_id=resource_config['image_id'],
        flavor_id=resource_config['flavor_id'],
        networks=resource_config['networks'],
        key_name=resource_config['key_name'],
        name=resource_config['name']
    )
    while True:
        server = connection.compute.find_server(server.id, ignore_missing=False)
        if server.status == 'ACTIVE':
            break
        elif server.status == 'ERROR':
            raise Exception('Failed creating server')
        else:
            time.sleep(2)
    connection.compute.add_security_group_to_server(server, sec_group_id)
    return server


def create_vm(connection, sec_group_id, config, instance_name, server_ids_dict):
    resource_config = _get_resource_config(connection, config, instance_name)
    server = _create_server(connection, resource_config, sec_group_id)
    server_id = server.id
    server_ids_dict[instance_name] = (str(server_id))
    resource_config['id'] = server_id
    floating_ip = _create_floating_ip(connection, config, resource_config)
    time.sleep(2)  # Waiting for the server to connect to the floating_ip
    floating_ip_address = floating_ip.floating_ip_address
    private_ip_address = _get_private_ip(connection, server_id)
    logger.info('Created the VM {0} with private-ip: {1}, '
                'public-ip: {2}'.format(instance_name, private_ip_address,
                                        floating_ip_address))
    return private_ip_address, floating_ip_address


def delete_vm(connection, server_id):
    connection.delete_server(server_id, wait=True, delete_ips=True)


def clean_openstack(connection, env_ids_dict=None):
    logger.info('Cleaning the Openstack environment')
    environment_ids_dict = (env_ids_dict or
                            get_dict_from_yaml('environment_ids.yaml'))
    for server, server_id in environment_ids_dict.items():
        if server != 'sec_group':
            logger.info('Deleting the server: {}'.format(server))
            delete_vm(connection, server_id)
    logger.info('Deleting the cluster security group')
    connection.delete_security_group(environment_ids_dict['sec_group'])
    logger.info('Successfully cleaned the Openstack environment')


def _update_environment_ids_file(servers_ids_dict):
    curr_env_ids = get_dict_from_yaml('environment_ids.yaml')
    with open('environment_ids.yaml', 'w') as f:
        curr_env_ids.update(servers_ids_dict)
        yaml.dump(curr_env_ids, f)


def handle_failure(connection, clean_openstack_env):
    traceback.print_exc()
    time.sleep(0.5)
    if clean_openstack_env:
        clean_openstack(connection)


def create_connection(config):
    return openstack.connect(
        auth_url=config['auth_url'],
        project_name=config['tenant_name'],
        username=config['username'],
        password=config['password'],
        region_name=config['region_name'],
        user_domain_name='Default',
        project_domain_name='Default'
    )


def _create_instances_names_list(config):
    instances_names = []
    instances_count = config['number_of_instances']
    for instance, instances_number in instances_count.items():
        if instance == 'postgresql' and instances_number < 2:
            raise Exception('PostgreSQL cluster must be more than 2 instances')
        elif instances_number < 1:
            raise Exception('A cluster must contain at least 1 instance')
        if config['using_load_balancer'] and \
                (instance == 'manager' and instances_number == 1):
            raise Exception('Cannot use a load-balancer with only one Manager')
        for i in range(instances_number):
            instances_names.append('{0}-{1}'.format(instance, i+1))
    if config['using_load_balancer']:
        instances_names.append('load_balancer')
    return instances_names


def create_openstack_vms(config, sec_group_id):
    logger.info('Creating VMs on Openstack')
    instances_names = _create_instances_names_list(config)
    instances = {}
    servers_ids_dict = {}
    connection = create_connection(config)
    logger.warning('The VMs security group opens all ports')
    try:
        for instance in instances_names:
            private_ip_address, floating_ip_address = create_vm(
                connection, sec_group_id, config, instance,
                servers_ids_dict)
            instances[instance] = (private_ip_address, floating_ip_address)
    finally:
        _update_environment_ids_file(servers_ids_dict)
    return instances, connection, servers_ids_dict
