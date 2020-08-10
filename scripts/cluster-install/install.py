#! /usr/bin/env python
from common import *
from openstack_connection import (create_sec_group_and_open_all_ports,
                                  create_connection,
                                  handle_failure,
                                  create_vm)


def _create_sec_group(connection, environment_ids_dict):
    sec_group = create_sec_group_and_open_all_ports(connection)
    environment_ids_dict['sec_group'] = (str(sec_group.id))
    return sec_group.id


def _create_jump_host(config, connection, sec_group_id, environment_ids_dict):
    logger.info('Creating the jump-host')
    return create_vm(connection, sec_group_id, config, 'jump-host',
                     environment_ids_dict)


def _prepare_jump_host(jump_host, jump_host_dir, config_path, license_path,
                       external_db_config):
    commands_list = [
        'sudo yum install -y epel-release',
        'sudo yum install -y python-pip',
        'sudo yum groupinstall -y \"Development Tools\"',
        'sudo yum install -y python-devel',
        'sudo pip install --upgrade pip==9.0.1',
        'sudo pip install -r {0}/requirements.txt'.format(jump_host_dir)
    ]
    scp_files_list = [
        'environment_ids.yaml',
        'install_from_jump_host.py',
        'common.py',
        'openstack_connection.py',
        'clean-openstack.py',
        'install_load_balancer.sh',
        'manager_config.yaml',
        'postgresql_config.yaml',
        'rabbitmq_config.yaml'
    ]
    if os.path.exists(EXISTING_VMS_PATH):
        scp_files_list.append(EXISTING_VMS_PATH)
    logger.info('Preparing the jump-host')
    jump_host.exec_command('mkdir {0}'.format(jump_host_dir))
    scp_local_to_remote(jump_host, 'requirements.txt', jump_host_dir)
    for command in commands_list:
        jump_host.exec_command(command)
    jump_host_ssh_key_path = JUMP_HOST_SSH_KEY_PATH.format(jump_host.username)
    jump_host_config_path = JUMP_HOST_CONFIG_PATH.format(jump_host.username)
    jump_host_license_path = JUMP_HOST_LICENSE_PATH.format(jump_host.username)
    scp_local_to_remote(jump_host, jump_host.key_path, jump_host_ssh_key_path)
    jump_host.exec_command('chmod 400 {0}'.format(jump_host_ssh_key_path))
    scp_local_to_remote(jump_host, config_path, jump_host_config_path)
    scp_local_to_remote(jump_host, license_path, jump_host_license_path)
    # If using external db we need to copy its CA cert too.
    if EXTERNAL_DB_CA_PATH_FIELD in external_db_config:
        scp_local_to_remote(jump_host,
                            external_db_config.get(EXTERNAL_DB_CA_PATH_FIELD),
                            jump_host_dir)

    for scp_file in scp_files_list:
        scp_local_to_remote(jump_host, scp_file, jump_host_dir)


def _run_install_script(jump_host, jump_host_dir):
    try:
        jump_host.exec_command('python {0}/install_from_jump_host.py'.
                               format(jump_host_dir))
    finally:
        scp_remote_to_local(jump_host,
                            JUMP_HOST_ENV_IDS.format(jump_host.username),
                            'environment_ids.yaml')


def _get_openstack_connection(config):
    try:
        return create_connection(config)
    except Exception:
        raise Exception('Couldn\'t craete a connection on Openstack. '
                        'Make sure the Openstack connection configuration'
                        'is correct')


def _validate_number_of_instances(number_of_instances, using_load_balancer,
                                  external_db_config):
    for instance, instances_number in number_of_instances.items():
        # number of postgres instances is 0 only if using external db
        if instance == 'postgresql' and instances_number in range(1, 3) and \
                not external_db_config:
            raise Exception(
                'PostgreSQL cluster must be more than 2 instances or 0 if'
                ' using external db')
        elif instances_number < 1 and instance != 'postgresql':
            raise Exception('A cluster must contain at least 1 instance')
        if using_load_balancer and \
                (instance == 'manager' and instances_number == 1):
            raise Exception('Cannot use a load-balancer with only one Manager')


def _number_of_existing_instances(existing_vms_dict):
    number_of_instances = {}
    for instance_type, instances_list in existing_vms_dict.items():
        if instance_type not in ('load_balancer', 'jump_host'):
            number_of_instances[instance_type] = len(instances_list)
    return number_of_instances


def _get_existing_vms_dict(existing_vms_list):
    existing_vms_dict = {}
    for vm in existing_vms_list:
        instance_type = vm.get('instance_type')
        existing_vms_dict.setdefault(instance_type, []).append(vm)
    return existing_vms_dict


def _validate_existing_vms(number_of_instances, using_load_balancer,
                           existing_vms_dict):
    if 'jump_host' not in existing_vms_dict:
        raise Exception('A jump_host must be specified in the existing_vms')
    if using_load_balancer != ('load_balancer' in existing_vms_dict):
        raise Exception('using_load_balancer value doesn\'t match the '
                        'existing VMs list')
    if _number_of_existing_instances(existing_vms_dict) != number_of_instances:
        raise Exception('number_of_instances doesn\'t match the existing_vms')


def _handle_existing_vms(existing_vms, number_of_instances,
                         using_load_balancer):
    existing_vms_dict = _get_existing_vms_dict(existing_vms)
    _validate_existing_vms(number_of_instances, using_load_balancer,
                           existing_vms_dict)
    jump_host_attr = existing_vms_dict.get('jump_host')[0]
    with open(EXISTING_VMS_PATH, 'w') as existing_vms_file:
        yaml.dump(existing_vms_dict, existing_vms_file)
    return jump_host_attr['private_ip'], jump_host_attr['public_ip']


def main():
    parse_args = parse_command()
    clean_openstack = parse_args.clean
    config_path = parse_args.config_path
    config = get_dict_from_yaml(config_path)
    key_path = config.get('key_file_path')
    existing_vms = config.get('existing_vms')
    vm_username = config.get('machine_username')
    license_path = config.get('cloudify_license_path')
    number_of_instances = config.get('number_of_instances')
    using_load_balancer = config.get('using_load_balancer')
    existing_security_group_id = config.get('existing_security_group_id')
    external_db_config = config.get(EXTERNAL_DB_CONFIGURATION_FIELD)
    _validate_number_of_instances(number_of_instances, using_load_balancer,
                                  external_db_config)
    connection = None
    environment_ids_dict = {}
    needs_connection = (not existing_security_group_id) or (not existing_vms)
    if needs_connection:
        connection = _get_openstack_connection(config)
    if not existing_vms:
        sec_group_id = (
            existing_security_group_id if existing_security_group_id
            else _create_sec_group(connection, environment_ids_dict))
    silent_remove(EXISTING_VMS_PATH)
    if existing_vms:
        jump_host_private_ip, jump_host_floating_ip = \
            _handle_existing_vms(existing_vms, number_of_instances,
                                 using_load_balancer)
    else:
        jump_host_private_ip, jump_host_floating_ip = \
            _create_jump_host(config, connection, sec_group_id,
                              environment_ids_dict)

    with open('environment_ids.yaml', 'w') as f:
        yaml.dump(environment_ids_dict, f)
    jump_host = VM(jump_host_private_ip, jump_host_floating_ip,
                   'jump-host', key_path, vm_username)
    jump_host_dir = JUMP_HOST_DIR.format(jump_host.username)
    try:
        _prepare_jump_host(jump_host, jump_host_dir, config_path, license_path,
                           external_db_config)
        _run_install_script(jump_host, jump_host_dir)
    except Exception:
        if needs_connection:
            handle_failure(connection, clean_openstack)
        raise
    logger.info('The jump-host public IP: {0}'.format(jump_host.public_ip))


if __name__ == "__main__":
    main()
