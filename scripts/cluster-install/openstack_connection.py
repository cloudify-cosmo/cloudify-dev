import time
import yaml
import traceback
import openstack


def _get_resource_config(connection, config, instance):
    image_attr = config.get('image_name') or config.get('image_id')
    flavor_attr = config.get('flavor_name') or config.get('flavor_id')
    network_attr = config.get('network_name') or config.get('network_id')
    image = connection.compute.find_image(image_attr)
    flavor = connection.compute.find_flavor(flavor_attr)
    network = connection.network.find_network(network_attr)
    resource_config = {
        'name': instance,
        'image_id': image.id,
        'flavor_id': flavor.id,
        'networks': [{'uuid': network.id}],
        'key_name': config['key_name'],
    }
    return resource_config


def _create_sec_group_and_open_all_ports(connection):
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


def _create_server(connection, resource_config, sec_group):
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
    connection.compute.add_security_group_to_server(server, sec_group)
    return server


def create_vm(connection, sec_group, config, instance_name,
              environment_ids_dict, logging):
    resource_config = _get_resource_config(connection, config, instance_name)
    server = _create_server(connection, resource_config, sec_group)
    server_id = server.id
    environment_ids_dict[instance_name] = (str(server_id))
    resource_config['id'] = server_id
    floating_ip = _create_floating_ip(connection, config, resource_config)
    floating_ip_address = floating_ip.floating_ip_address
    private_ip_address = _get_private_ip(connection, server_id)
    _add_floating_ip_to_server(connection, server_id, floating_ip_address)
    logging.info('Created the VM {0} with private-ip: {1}, public-ip: {2}'.
                 format(instance_name, private_ip_address, floating_ip_address))
    return private_ip_address, floating_ip_address


def delete_vm(connection, server_id):
    connection.delete_server(server_id, wait=True, delete_ips=True)


def clean_openstack(connection, environment_ids_dict, logging):
    logging.info('Cleaning the Openstack environment')
    for server, server_id in environment_ids_dict.items():
        if server != 'sec_group':
            logging.info('deleting the server: {}'.format(server))
            delete_vm(connection, server_id)
    logging.info('deleting the cluster security group')
    connection.delete_security_group(environment_ids_dict['sec_group'])
    logging.info('Successfully cleaned the Openstack environment')


def _create_environment_ids_file(environment_ids_dict):
    with open('environment_ids.yaml', 'w') as f:
        yaml.dump(environment_ids_dict, f)


def handle_failure(connection, environment_ids_dict, clean_openstack_env, 
                   logging):
    traceback.print_exc()
    time.sleep(0.5)
    _create_environment_ids_file(environment_ids_dict)
    if clean_openstack_env:
        clean_openstack(connection, environment_ids_dict, logging)


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
    instances_names = ['factory']
    instances_count = config['number_of_instances']
    for instance, instances_number in instances_count.iteritems():
        if instance == 'postgresql' and instances_number < 2:
            raise Exception('PostgreSQL cluster must be more than 2 instances')
        elif instances_number < 1:
            raise Exception('A cluster must contain at least 1 instance')
        for i in range(instances_number):
            instances_names.append('{0}-{1}'.format(instance, i+1))
    if config['using_load_balancer']:
        instances_names.append('load_balancer')
    return instances_names


def create_openstack_vms(config, logging, clean_openstack_env):
    logging.info('Creating VMs on Openstack')
    instances_names = _create_instances_names_list(config)
    instances = {}
    environment_ids_dict = {}
    connection = create_connection(config)
    logging.warning('The VMs security group opens all ports')
    sec_group = _create_sec_group_and_open_all_ports(connection)
    environment_ids_dict['sec_group'] = (str(sec_group.id))
    try:
        for instance in instances_names:
            private_ip_address, floating_ip_address = create_vm(
                connection, sec_group, config, instance, environment_ids_dict,
                logging)
            instances[instance] = (private_ip_address, floating_ip_address)
    except Exception:
        handle_failure(connection, environment_ids_dict, clean_openstack_env,
                       logging)
        exit(0)
    _create_environment_ids_file(environment_ids_dict)
    return instances, connection, environment_ids_dict
