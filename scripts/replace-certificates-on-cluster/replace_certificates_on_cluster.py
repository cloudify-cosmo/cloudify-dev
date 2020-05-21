import time
from contextlib import contextmanager

import yaml
import argparse
import paramiko

MANAGER = 'manager'
POSTGRESQL = 'postgresql'
RABBITMQ = 'rabbitmq'

POSTGRESQL_CERTS_LOCATIONS = [
    '/var/lib/patroni/db.{0}',
    '/var/lib/patroni/rest.{0}',
    '/etc/etcd/etcd.{0}'
]

RABBITMQ_CERTS_LOCATIONS = [
    '/etc/cloudify/ssl/rabbitmq-{0}'
]


class Node(object):
    def __init__(self, host_ip, username, key_path, new_cert_path,
                 new_cert_key_path):
        if bool(new_cert_path) != bool(new_cert_key_path):
            raise AttributeError('You must specify both cert_path and '
                                 'key_path or none of them')
        self.key_path = key_path
        self.host_ip = host_ip
        self.username = username
        self.new_cert_path = new_cert_path
        self.new_cert_key_path = new_cert_key_path
        self.client = create_ssh_client(self.host_ip, self.username,
                                        self.key_path)

    def scp_to_node(self, local_path, remote_path):
        with get_sftp(self.client) as sftp:
            sftp.put(local_path, remote_path)


def _retry_with_sleep(func, *func_args, **kwargs):
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


def create_ssh_client(hostname, username, key_file):
    return _retry_with_sleep(_create_ssh_client_func, hostname, username,
                             key_file)  # waiting for the VM to run


@contextmanager
def get_sftp(ssh_client):
    sftp = ssh_client.open_sftp()
    try:
        yield sftp
    finally:
        if sftp:
            sftp.close()
        ssh_client.close()


def get_dict_from_yaml(yaml_path):
    with open(yaml_path) as f:
        return yaml.load(f, yaml.Loader)


def parse_command():
    parser = argparse.ArgumentParser(description='Replacing certificates on '
                                                 'a Cloudify cluster')
    parser.add_argument('--config-path', action='store', type=str,
                        required=True, help='The configuration.yaml file path')
    return parser.parse_args()


def handle_manager_certificates(nodes_list, ca_cert_path,
                                external_certificates):
    pass


def handle_rabbitmq_certificates(nodes_list, new_ca_cert_path):
    for node in nodes_list:
        if new_ca_cert_path:
            _rabbitmq_replace_ca_certs(node, new_ca_cert_path)
        _postgres_replace_certs(node)


def handle_postgresql_certificates(nodes_list, new_ca_cert_path):
    for node in nodes_list:
        if new_ca_cert_path:
            _postgres_replace_ca_certs(node, new_ca_cert_path)
        _postgres_replace_certs(node)


def _rabbitmq_replace_certs(node):
    certs_location = ['/etc/cloudify/ssl/rabbitmq-{0}.pem']
    _replace_node_certs(node, certs_location)


def _rabbitmq_replace_ca_certs(node, new_ca_cert_path):
    ca_certs_locations = [
        '/etc/cloudify/ssl/rabbitmq-ca.pem',
        '/etc/cloudify/ssl/status_reporter_cert.pem'
    ]
    _replace_node_ca_certs(node, new_ca_cert_path, ca_certs_locations)


def _postgres_replace_certs(node):
    postgres_certs_locations = [
        '/var/lib/patroni/db.{0}',
        '/var/lib/patroni/rest.{0}',
        '/etc/etcd/etcd.{0}'
    ]
    _replace_node_certs(node, postgres_certs_locations)


def _postgres_replace_ca_certs(node, new_ca_cert_path):
    ca_certs_locations = [
        '/var/lib/patroni/ca.crt',
        '/etc/cloudify/ssl/status_reporter_cert.pem',
        '/etc/etcd/ca.crt'
    ]
    _replace_node_ca_certs(node, new_ca_cert_path, ca_certs_locations)


def _replace_node_ca_certs(node, new_ca_cert_path, ca_certs_locations):
    for ca_location in ca_certs_locations:
        node.scp_to_node(new_ca_cert_path, ca_location)


def _replace_node_certs(node, certs_locations):
    for new_location in certs_locations:
        node.scp_to_node(node.new_cert_path, new_location.format('crt'))
        node.scp_to_node(node.new_cert_key_path, new_location.format('key'))


def create_nodes_list(nodes, username, key_path):
    return [Node(node.get('host_ip'), username, key_path, node.get('cert_path'),
                 node.get('key_path')) for node in nodes if node.get('host_ip')]


def main():
    parse_args = parse_command()
    config = get_dict_from_yaml(parse_args.config_path)
    key_path = config.get('key_file_path')
    username = config.get('username')
    instances = config.get('instances')

    for instance in config.get('instances'):
        ca_cert_path = instance.get('ca_cert_path')
        nodes_list = create_nodes_list(instance.get('nodes'), username,
                                       key_path)
        if instance == MANAGER and nodes_list:
            handle_manager_certificates(nodes_list, ca_cert_path,
                                        instance.get('external_certificates'))
        elif instance == RABBITMQ and nodes_list:
            handle_rabbitmq_certificates(nodes_list, ca_cert_path)
        elif instance == POSTGRESQL and nodes_list:
            handle_postgresql_certificates(nodes_list, ca_cert_path)


if __name__ == '__main__':
    main()
