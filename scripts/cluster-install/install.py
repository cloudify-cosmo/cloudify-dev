#! /usr/bin/env python
import yaml
import logging

from common import *
from openstack_connection import (create_sec_group_and_open_all_ports,
                                  create_connection,
                                  handle_failure,
                                  create_vm)


def _create_jump_host(config, connection, environment_ids_dict):
    sec_group = create_sec_group_and_open_all_ports(connection)
    environment_ids_dict['sec_group'] = (str(sec_group.id))
    return create_vm(connection, sec_group.id, config, 'jump-host',
                     environment_ids_dict, logging)


def _prepare_jump_host(jump_host, jump_host_dir, config_path, license_path):
    commands_list = [
        'sudo yum install -y epel-release',
        'sudo yum install -y python-pip',
        'sudo yum groupinstall -y \"Development Tools\"',
        'sudo yum install -y python-devel',
        'sudo pip install -y -r {0}/requirements.txt'.format(jump_host_dir)
    ]
    jump_host.exec_command('mkdir {0}'.format(jump_host_dir))
    scp_local_to_remote(jump_host, 'requirements.txt', jump_host_dir)
    for command in commands_list:
        jump_host.exec_command(command)
    scp_local_to_remote(jump_host.key_path, jump_host.key_path,
                        JUMP_HOST_SSH_KEY_PATH.format(jump_host.username))
    jump_host.exec_command('chmod 400 {0}'.format(JUMP_HOST_SSH_KEY_PATH))
    scp_local_to_remote(jump_host, config_path, JUMP_HOST_CONFIG_PATH)
    scp_local_to_remote(jump_host, 'parsed_flags.yaml', JUMP_HOST_DIR)
    scp_local_to_remote(jump_host, license_path, JUMP_HOST_LICENSE_PATH)
    scp_local_to_remote(jump_host, 'environment_ids.yaml', JUMP_HOST_DIR)
    scp_local_to_remote(jump_host, 'install_from_jump_host.py', JUMP_HOST_DIR)


def _run_install_script(jump_host):
    jump_host.exec_command('python {0}/install_from_jump_host.py'.
                           format(JUMP_HOST_DIR))


def main():
    parse_args = parse_command()
    clean_openstack = parse_args.clean
    logging.basicConfig(level=logging.INFO)
    config_path = parse_args.config_path
    config = get_dict_from_yaml(config_path)
    key_path = config.get('key_file_path')
    vm_username = config.get('machine_username')
    license_path = config.get('cloudify_license_path')
    environment_ids_dict = {}
    connection = create_connection(config)
    jump_host_private_ip, jump_host_floating_ip = \
        _create_jump_host(config, connection, environment_ids_dict)
    with open('environment_ids.yaml', 'w') as f:
        yaml.dump(environment_ids_dict, f)
    jump_host = VM(jump_host_private_ip, jump_host_floating_ip,
                   'jump-host', key_path, vm_username)
    jump_host_dir = JUMP_HOST_DIR.format(jump_host.username)
    _prepare_jump_host(jump_host, jump_host_dir, config_path, license_path)
    try:
        _run_install_script(jump_host)
    except Exception:
        scp_remote_to_local(jump_host, JUMP_HOST_ENV_IDS,
                            'environment_ids.yaml')
        handle_failure(connection, clean_openstack, logging)
        exit(1)
    scp_remote_to_local(jump_host, JUMP_HOST_ENV_IDS, 'environment_ids.yaml')
    # TODO: handle errors


if __name__ == "__main__":
    main()
