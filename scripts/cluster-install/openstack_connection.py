import time
import traceback
import openstack


def _get_client_config(config):
    client_config = {
        'auth_url': config['auth_url'],
        'username': config['username'],
        'password': config['password'],
        'region_name': config['region_name'],
        'project_name': config['tenant_name'],
        'user_domain_name': 'Default',
        'project_domain_id': 'Default'
    }
    return client_config


def _get_resource_config(config, name):
    resource_config = {
        'name': name,
        'image_id': config['image_id'],
        'flavor_id': config['flavor_id'],
        'networks': [{'uuid': config['network_id']}],
        'key_name': config['key_name']
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
        if (end_time-start_time) > 40 and tmp_server.private_v4 == '':
            raise Exception('Could not get the private ip of the server: {}'
                            .format(server_id))  # Timeout
    return tmp_server.private_v4


def _create_floating_ip(connection, config, resource_config):
    return connection.create_floating_ip(network=config['gateway_net_id'],
                                         server=resource_config)


def _add_floating_ip_to_server(connection, server_id, floating_ip_address):
    connection.compute.add_floating_ip_to_server(server_id,
                                                 floating_ip_address)


def create_vm(connection, sec_group, config, instance, environment_ids_dict,
              logging):
    resource_config = _get_resource_config(config, instance)
    server = connection.compute.create_server(**resource_config)
    server_id = server.id
    environment_ids_dict[instance] = (str(server_id))
    resource_config['id'] = server_id
    floating_ip = _create_floating_ip(connection, config, resource_config)
    floating_ip_address = floating_ip.floating_ip_address
    private_ip_address = _get_private_ip(connection, server_id)
    _add_floating_ip_to_server(connection, server_id, floating_ip_address)
    connection.compute.add_security_group_to_server(server, sec_group)
    logging.info('Created the VM {0} with private-ip: {1}, public-ip: {2}'.
                 format(instance, private_ip_address, floating_ip_address))
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


def handle_failure(connection, environment_ids_dict, clean_openstack_env, 
                   logging):
    traceback.print_exc()
    time.sleep(0.5)
    if clean_openstack_env:
        clean_openstack(connection, environment_ids_dict, logging)


def create_connection(config):
    client_config = _get_client_config(config)
    return openstack.connect(**client_config)


def _create_instances_names_list(config):
    instances_names = ['factory']
    instances_count = config['number_of_instances']
    for instance, instances_number in instances_count.iteritems():
        # if instance == 'postgresql' and instances_number < 2:
        #     raise Exception('PostgreSQL cluster must be more than 2 instances')
        for i in range(instances_number):
            instances_names.append('{0}_{1}'.format(instance, i+1))
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
    return instances, connection, environment_ids_dict
