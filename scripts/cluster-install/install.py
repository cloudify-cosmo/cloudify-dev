#! /usr/bin/env python
from common import *
from openstack_connection import (create_sec_group_and_open_all_ports,
                                  create_connection,
                                  handle_failure,
                                  create_vm)


def _create_sec_group(connection, environment_ids_dict):
    sec_group = create_sec_group_and_open_all_ports(connection)
    environment_ids_dict['sec_group'] = (str(sec_group.id))
    return sec_group


def _create_jump_host(config, connection, sec_group, environment_ids_dict):
    logger.info('Creating the jump-host')
    return create_vm(connection, sec_group.id, config, 'jump-host',
                     environment_ids_dict)


def _prepare_jump_host(jump_host, jump_host_dir, config_path, license_path):
    commands_list = [
        'sudo yum install -y epel-release',
        'sudo yum install -y python-pip',
        'sudo yum groupinstall -y \"Development Tools\"',
        'sudo yum install -y python-devel',
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
    for scp_file in scp_files_list:
        scp_local_to_remote(jump_host, scp_file, jump_host_dir)


def _run_install_script(jump_host, jump_host_dir):
    try:
        jump_host.exec_command('python {0}/install_from_jump_host.py'.
                               format(jump_host_dir))
    except Exception:
        scp_remote_to_local(jump_host,
                            JUMP_HOST_ENV_IDS.format(jump_host.username),
                            'environment_ids.yaml')
        raise


def main():
    parse_args = parse_command()
    clean_openstack = parse_args.clean
    config_path = parse_args.config_path
    config = get_dict_from_yaml(config_path)
    key_path = config.get('key_file_path')
    vm_username = config.get('machine_username')
    license_path = config.get('cloudify_license_path')
    environment_ids_dict = {}
    connection = create_connection(config)
    sec_group = _create_sec_group(connection, environment_ids_dict)
    jump_host_private_ip, jump_host_floating_ip = \
        _create_jump_host(config, connection, sec_group, environment_ids_dict)
    with open('environment_ids.yaml', 'w') as f:
        yaml.dump(environment_ids_dict, f)
    jump_host = VM(jump_host_private_ip, jump_host_floating_ip,
                   'jump-host', key_path, vm_username)
    jump_host_dir = JUMP_HOST_DIR.format(jump_host.username)
    try:
        _prepare_jump_host(jump_host, jump_host_dir, config_path, license_path)
        _run_install_script(jump_host, jump_host_dir)
    except Exception:
        handle_failure(connection, clean_openstack)
        exit(1)
    logger.info('The jump-host public IP: {0}'.format(jump_host.public_ip))
    scp_remote_to_local(jump_host,
                        JUMP_HOST_ENV_IDS.format(jump_host.username),
                        'environment_ids.yaml')


if __name__ == "__main__":
    main()
