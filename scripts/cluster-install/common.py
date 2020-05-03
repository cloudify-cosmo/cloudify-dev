import os
import sys
import time
import errno
import select
import logging

import yaml
import argparse
import paramiko


def init_logger():
    log = logging.getLogger('cluster_install')
    log.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter) 
    log.addHandler(handler)
    return log


logger = init_logger()

EXISTING_VMS_PATH = 'existing_vms.yaml'
JUMP_HOST_DIR = '/home/{0}/cluster_install'
JUMP_HOST_SSH_KEY_PATH = '/home/{0}/.ssh/jump_host_key'
JUMP_HOST_ENV_IDS = JUMP_HOST_DIR + '/environment_ids.yaml'
JUMP_HOST_CONFIG_PATH = JUMP_HOST_DIR + '/config_env.yaml'
JUMP_HOST_LICENSE_PATH = JUMP_HOST_DIR + '/cloudify_license.yaml'
JUMP_HOST_PARSED_FLAGS_PATH = JUMP_HOST_DIR + '/parsed_flags.yaml'
JUMP_HOST_INSTALL_PATH = JUMP_HOST_DIR + '/install_from_jump_host.py'


def retry_with_sleep(func, *func_args, **kwargs):
    retry_count = kwargs.get('retry_count', 15)
    delay = kwargs.get('delay', 2)
    for i in range(retry_count):
        try:
            return func(*func_args)
        except Exception as e:
            if i < retry_count - 1:
                time.sleep(delay)
                continue
            else:
                raise e


def _create_ssh_client_func(hostname, username, key_file):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=hostname, username=username, key_filename=key_file)
    return client


def _create_ssh_client(hostname, username, key_file):
    return retry_with_sleep(_create_ssh_client_func, hostname, username,
                            key_file)  # waiting for the VM to run


def _blocking_exec_command(client, command):
    # one channel per command
    stdin, stdout, stderr = client.exec_command(command)
    # get the shared channel for stdout/stderr/stdin
    channel = stdout.channel
    output = ''

    # we do not need stdin.
    stdin.close()
    # indicate that we're not going to write to that channel anymore
    channel.shutdown_write()

    # read stdout/stderr in order to prevent read block hangs
    print(stdout.channel.recv(len(stdout.channel.in_buffer)))
    # chunked read to prevent stalls
    while not channel.closed or channel.recv_ready() or \
            channel.recv_stderr_ready():
        # stop if channel was closed prematurely, and there is no data in the
        # buffers.

        got_chunk = False
        readq, _, _ = select.select([stdout.channel], [], [], 180)
        for c in readq:
            if c.recv_ready():
                output = stdout.channel.recv(len(c.in_buffer))
                print(output)
                got_chunk = True
            if c.recv_stderr_ready():
                # make sure to read stderr to prevent stall
                output = stderr.channel.recv_stderr(len(c.in_stderr_buffer))
                got_chunk = True

        if not got_chunk \
                and stdout.channel.exit_status_ready() \
                and not stderr.channel.recv_stderr_ready() \
                and not stdout.channel.recv_ready():
            # indicate that we're not going to read from this channel anymore
            stdout.channel.shutdown_read()
            # close the channel
            stdout.channel.close()
            break  # exit as remote side is finished and our bufferes are empty

    # close all the pseudofiles
    stdout.close()
    stderr.close()

    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        raise Exception(output)
    
    return output
    

def close_clients_connection(clients_list):
    for client in clients_list:
        client.close()


class VM(object):
    def __init__(self, private_ip, public_ip, name, key_path, vm_username):
        self.private_ip = private_ip
        self.public_ip = public_ip
        self.name = name
        self.key_path = key_path
        self.username = vm_username
        self.client = _create_ssh_client(self.public_ip, self.username,
                                         self.key_path)

    def exec_command(self, command):
        logger.debug('Running `{0}` on {1}'.format(command, self.name))
        return _blocking_exec_command(self.client, command)

    def _is_cluster_instance(self):
        cluster_instances = ['postgresql', 'rabbitmq', 'manager']
        for instance in cluster_instances:
            if instance in self.name:
                return True
        return False

    def get_node_id(self):
        if not self._is_cluster_instance():
            return
        stdout = self.exec_command('cfy_manager node get-id')
        return stdout[16:52]


def scp_local_to_remote(instance, source_path, destination_path):
    os.system('scp -i {key_path} -o StrictHostKeyChecking=no -r '
              '{source_path} {username}@{public_ip}:{destination_path}'.
              format(key_path=instance.key_path, source_path=source_path,
                     username=instance.username, public_ip=instance.public_ip,
                     destination_path=destination_path))


def scp_remote_to_local(instance, source_path, destination_path):
    os.system('scp -i {key_path} -o StrictHostKeyChecking=no -r '
              '{username}@{public_ip}:{source_path} {destination_path}'.
              format(key_path=instance.key_path, source_path=source_path,
                     username=instance.username, public_ip=instance.public_ip,
                     destination_path=destination_path))


def parse_command():
    parser = argparse.ArgumentParser(description='Installing an Active-Active '
                                                 'manager cluster')
    parser.add_argument('--config-path', action='store', type=str,
                        required=True, help='The config_env.yaml file path')
    parser.add_argument('--clean-on-failure', dest='clean',
                        action='store_true', default=False,
                        help='Pass this flag if you want to clean your '
                             'Openstack environment on failure.\n'
                             'In the case of using existing VMs, the '
                             'environment won\'t be deleted.')
    return parser.parse_args()


def get_dict_from_yaml(yaml_path):
    with open(yaml_path) as f:
        yaml_dict = yaml.load(f, yaml.Loader)
    return yaml_dict


def silent_remove(filename):
    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT:  # errno.ENOENT = no such file or directory
            raise  # re-raise exception if a different error occurred
