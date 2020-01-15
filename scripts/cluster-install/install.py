#! /usr/bin/env python
from __future__ import print_function
import os
import yaml
import json
import time
import string
import random
import logging
import paramiko
import argparse
from openstack_connection import create_openstack_vms, handle_failure, delete_vm

CERT_PATH = '~/.cloudify-test-ca'
LOCAL_INSTALL_CLUSTER = '/tmp/install_cluster'
LOCAL_INSTALL_CLUSTER_CERTS = '{}/certs'.format(LOCAL_INSTALL_CLUSTER)
REMOTE_PARENT_DIRECTORY = '/tmp'
REMOTE_INSTALL_CLUSTER = '{}/install_cluster'.format(REMOTE_PARENT_DIRECTORY)


def retry_with_sleep(func, *func_args, **kwargs):
    retry_count = kwargs.get('retry_count', 10)
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
    stdin, stdout, stderr = client.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        raise Exception(stdout.read())
    return stdin, stdout, stderr


def _close_clients_connection(clients_list):
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
        stdin, stdout, stderr = self.exec_command('cfy_manager node get-id')
        return stdout.read()[16:52]


def scp_local_to_remote(key_path, instance, source_path, destination_path):
    os.system('scp -i {key_path} -o StrictHostKeyChecking=no -r '
              '{source_path} {username}@{public_ip}:{destination_path}'.
              format(key_path=key_path, source_path=source_path,
                     username=instance.username, public_ip=instance.public_ip,
                     destination_path=destination_path))


def scp_remote_to_local(key_path, instance, source_path, destination_path):
    os.system('scp -i {key_path} -o StrictHostKeyChecking=no -r '
              '{username}@{public_ip}:{source_path} {destination_path}'.
              format(key_path=key_path, source_path=source_path,
                     username=instance.username, public_ip=instance.public_ip,
                     destination_path=destination_path))


def _create_instances_list(instances_dict, include_load_balancer=True):
    instances_list = []
    instances = ['postgresql', 'rabbitmq', 'manager']
    for instance in instances:
        instances_list.extend(instances_dict[instance])
    if include_load_balancer and 'load_balancer' in instances_dict:
        instances_list.extend(instances_dict['load_balancer'])
    return instances_list


def _generate_instance_certificate(factory, instance):
    factory.exec_command('cfy_manager generate-test-cert -s {0},{1}'.
                         format(instance.private_ip, instance.public_ip))
    factory.exec_command('mv {0}/{1}.crt {0}/{2}_cert.pem'.format(
        CERT_PATH, instance.private_ip, instance.name))
    factory.exec_command('mv {0}/{1}.key {0}/{2}_key.pem'.format(
        CERT_PATH, instance.private_ip, instance.name))


def _copy_certificates_to_local_directory(factory, key_path):
    scp_remote_to_local(key_path, factory, CERT_PATH,
                        LOCAL_INSTALL_CLUSTER_CERTS)
    os.system('mv {0}/.cloudify-test-ca/* {0}'.format(
        LOCAL_INSTALL_CLUSTER_CERTS))
    os.rmdir(os.path.join(LOCAL_INSTALL_CLUSTER_CERTS, '.cloudify-test-ca'))


def _generate_certs(instances_dict, key_path, download_link, rpm_name):
    logging.info('Generating certificates')
    factory = instances_dict['factory'][0]
    factory.exec_command('curl -O {0}'.format(download_link))
    factory.exec_command('sudo yum install -y {}'.format(rpm_name))
    instances_list = _create_instances_list(instances_dict)
    for instance in instances_list:
        _generate_instance_certificate(factory, instance)
    factory.exec_command('cp {0}/ca.crt {0}/ca.pem'.format(CERT_PATH))
    _copy_certificates_to_local_directory(factory, key_path)


def _write_crt_to_config(config_file, node_name, config_section):
    config_file[config_section]['cert_path'] = \
        REMOTE_INSTALL_CLUSTER + '/certs/{}_cert.pem'.format(node_name)
    config_file[config_section]['key_path'] = \
        REMOTE_INSTALL_CLUSTER + '/certs/{}_key.pem'.format(node_name)
    config_file[config_section]['ca_path'] = REMOTE_INSTALL_CLUSTER + \
                                             '/certs/ca.pem'
    conf_file_name = LOCAL_INSTALL_CLUSTER + '/config_files/{}_config.yaml' \
        .format(node_name)
    return conf_file_name


def _get_postgresql_cluster_members(postgresql_instances, include_node_id):
    postgresql_cluster = {
        postgresql_instances[j].name: {'ip': postgresql_instances[j].private_ip}
        for j in range(len(postgresql_instances))}
    if include_node_id:
        for j in range(len(postgresql_instances)):
            postgresql_cluster[postgresql_instances[j].name]['node_id'] = \
                postgresql_instances[j].get_node_id()
    return postgresql_cluster


def _prepare_postgresql_config_files(instances_dict):
    for node in instances_dict['postgresql']:
        with open('postgresql_config.yaml') as f:
            config_file = yaml.load(f, yaml.Loader)
        conf_file_name = _write_crt_to_config(config_file, node.name,
                                              'postgresql_server')
        config_file['postgresql_server']['cluster']['nodes'] = \
            _get_postgresql_cluster_members(instances_dict['postgresql'], False)
        with open(conf_file_name, 'w') as f:
            yaml.dump(config_file, f)


def _rabbitmq_credential_generator():
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for
                   _ in range(6))


def _get_rabbitmq_cluster_members(rabbitmq_instances, include_node_id):
    rabbitmq_cluster = {
        rabbitmq_instances[j].name: {
            'networks': {'default': rabbitmq_instances[j].private_ip}
        } for j in range(len(rabbitmq_instances))}
    if include_node_id:
        for j in range(len(rabbitmq_instances)):
            rabbitmq_cluster[rabbitmq_instances[j].name]['node_id'] = \
                rabbitmq_instances[j].get_node_id()
    return rabbitmq_cluster


def _prepare_rabbitmq_config_files(instances_dict):
    first_rabbitmq = instances_dict['rabbitmq'][0]
    rabbitmq_username = _rabbitmq_credential_generator()
    rabbitmq_password = _rabbitmq_credential_generator()
    for i, node in enumerate(instances_dict['rabbitmq']):
        with open('rabbitmq_config.yaml') as f:
            config_file = yaml.load(f, yaml.Loader)
        config_file['rabbitmq']['username'] = rabbitmq_username
        config_file['rabbitmq']['password'] = rabbitmq_password
        config_file['rabbitmq']['cluster_members'] = \
            _get_rabbitmq_cluster_members(instances_dict['rabbitmq'], False)
        conf_file_name = _write_crt_to_config(config_file, node.name,
                                              'rabbitmq')
        config_file['rabbitmq']['nodename'] = node.name
        if i != 0:
            config_file['rabbitmq']['join_cluster'] = first_rabbitmq.name
        with open(conf_file_name, 'w') as f:
            yaml.dump(config_file, f, default_flow_style=False)
    return rabbitmq_username, rabbitmq_password


def _create_ssl_inputs(node_name):
    ssl_inputs = {}
    cert = REMOTE_INSTALL_CLUSTER + '/certs/{}_cert.pem'.format(node_name)
    key = REMOTE_INSTALL_CLUSTER + '/certs/{}_key.pem'.format(node_name)
    ca = REMOTE_INSTALL_CLUSTER + '/certs/ca.pem'
    cert_path_list = ['internal_cert_path', 'external_cert_path',
                      'postgresql_client_cert_path']
    key_path_list = ['internal_key_path', 'external_key_path',
                     'postgresql_client_key_path']
    ca_path_list = ['ca_cert_path', 'external_ca_cert_path']
    for cert_path in cert_path_list:
        ssl_inputs[cert_path] = cert
    for key_path in key_path_list:
        ssl_inputs[key_path] = key
    for ca_path in ca_path_list:
        ssl_inputs[ca_path] = ca
    return ssl_inputs


def _prepare_manager_config_files(instances_dict, rabbitmq_credentials):
    ca_path = REMOTE_INSTALL_CLUSTER + '/certs/ca.pem'
    for node in instances_dict['manager']:
        with open('manager_config.yaml') as f:
            config_file = yaml.load(f, yaml.Loader)
        config_file['manager']['hostname'] = node.name
        config_file['manager']['cloudify_license_path'] = \
            REMOTE_INSTALL_CLUSTER + '/license.yaml'
        config_file['rabbitmq']['cluster_members'] = \
            _get_rabbitmq_cluster_members(instances_dict['rabbitmq'], True)
        config_file['rabbitmq']['username'] = rabbitmq_credentials[0]
        config_file['rabbitmq']['password'] = rabbitmq_credentials[1]
        config_file['rabbitmq']['ca_path'] = ca_path
        config_file['postgresql_server']['cluster']['nodes'] = \
            _get_postgresql_cluster_members(instances_dict['postgresql'], True)
        config_file['postgresql_server']['ca_path'] = ca_path
        if instances_dict['load_balancer']:
            config_file['agent']['networks']['default'] = \
                instances_dict['load_balancer'][0].private_ip
        config_file['ssl_inputs'] = _create_ssl_inputs(node.name)
        suffix = '/config_files/{}_config.yaml'.format(node.name)
        conf_file_name = LOCAL_INSTALL_CLUSTER + suffix
        with open(conf_file_name, 'w') as f:
            yaml.dump(config_file, f)


def _prepare_postgres_rabbit_config_files(instances_dict):
    logging.info('Preparing config files')
    os.mkdir(LOCAL_INSTALL_CLUSTER + '/config_files')
    _prepare_postgresql_config_files(instances_dict)
    rabbitmq_credentials = _prepare_rabbitmq_config_files(instances_dict)
    return rabbitmq_credentials


def _download_manager_and_create_license(license_path, download_link):
    os.system('cd {0} && curl -O {1}'.format(LOCAL_INSTALL_CLUSTER,
                                             download_link))
    os.system('cp {0} {1}'.format(
        license_path, os.path.join(LOCAL_INSTALL_CLUSTER, 'license.yaml')))


def _install_cluster_instances(cluster_members, key_path, rpm_name):
    for instance in cluster_members:
        logging.info('Installing {}'.format(instance.name))
        scp_local_to_remote(key_path, instance, LOCAL_INSTALL_CLUSTER,
                            REMOTE_PARENT_DIRECTORY)
        instance.exec_command('sudo yum install -y {rpm}'.format(
            rpm=os.path.join(REMOTE_INSTALL_CLUSTER, rpm_name)))
        instance.exec_command('cp {0}/config_files/{1}_config.yaml '
                              '/etc/cloudify/config.yaml'.
                              format(REMOTE_INSTALL_CLUSTER, instance.name))
        install_command = 'cfy_manager install --private-ip {0} --public-ip ' \
                          '{1}'.format(instance.private_ip, instance.public_ip)
        stdin, stdout, stderr = instance.exec_command(install_command)
        print(stdout.read())
        time.sleep(0.5)  # Avoiding running over the print by the next logging


def _install_instances(instances_dict, key_path, rpm_name, rabbitmq_cred):
    logging.info('Installing instances')
    _install_cluster_instances(instances_dict['postgresql'], key_path, rpm_name)
    _install_cluster_instances(instances_dict['rabbitmq'], key_path, rpm_name)
    _prepare_manager_config_files(instances_dict, rabbitmq_cred)
    _install_cluster_instances(instances_dict['manager'], key_path, rpm_name)


def _get_reporters_tokens(manager):
    stdin, stdout, stderr = manager.exec_command('cfy_manager status-reporter '
                                                 'get-tokens --json')
    reporters_tokens = json.loads(stdout.read())
    return (reporters_tokens['db_status_reporter'],
            reporters_tokens['broker_status_reporter'])


def _configure_postgresql_status_reporter(postgresql_instances,
                                          postgresql_reporter_token,
                                          managers_ips):
    logging.info('Configuring status_reporter')
    cmd = 'cfy_manager status-reporter configure --managers-ip {managers_ips}' \
          ' --token {token} --ca-path {ca_path} --reporting-freq 5 ' \
          '--user-name db_status_reporter'. \
        format(managers_ips=managers_ips, token=postgresql_reporter_token,
               ca_path=REMOTE_INSTALL_CLUSTER + '/certs/ca.pem')
    for postgresql in postgresql_instances:
        postgresql.exec_command(cmd)


def _configure_rabbitmq_status_reporter(rabbitmq_instances,
                                        rabbitmq_reporter_token,
                                        managers_ips):
    cmd = 'cfy_manager status-reporter configure --managers-ip {managers_ips}' \
          ' --token {token} --ca-path {ca_path} --reporting-freq 5 ' \
          '--user-name broker_status_reporter'. \
        format(managers_ips=managers_ips, token=rabbitmq_reporter_token,
               ca_path=REMOTE_INSTALL_CLUSTER + '/certs/ca.pem')
    for rabbitmq in rabbitmq_instances:
        rabbitmq.exec_command(cmd)


def _configure_status_reporter(instances_dict):
    postgresql_reporter_token, rabbitmq_reporter_token = \
        _get_reporters_tokens(instances_dict['manager'][0])
    managers_ips = ''
    for manager in instances_dict['manager']:
        managers_ips += manager.private_ip + ' '
    _configure_postgresql_status_reporter(instances_dict['postgresql'],
                                          postgresql_reporter_token,
                                          managers_ips)
    _configure_rabbitmq_status_reporter(instances_dict['rabbitmq'],
                                        rabbitmq_reporter_token, managers_ips)


def _get_vm(instances_details, instance, key_path, vm_username):
    private_ip = str(instances_details[instance][0])
    public_ip = str(instances_details[instance][1])
    return VM(private_ip, public_ip, instance, key_path, vm_username)


def _get_instance_group(instance_name):
    groups = ['manager', 'postgresql', 'rabbitmq', 'factory', 'load_balancer']
    for group in groups:
        if group in instance_name:
            return group


def _get_instances_dict(instances_details, key_path, vm_username):
    instances_dict = {'postgresql': [], 'rabbitmq': [],
                      'manager': [], 'factory': [], 'load_balancer': []}
    for instance_name in instances_details:
        instance_vm = _get_vm(instances_details, instance_name, key_path,
                              vm_username)
        instance_group = _get_instance_group(instance_name)
        instances_dict[instance_group].append(instance_vm)
    for _, instance_items in instances_dict.iteritems():
        if len(instance_items) > 1:
            instance_items.sort(key=lambda x: int(x.name.rsplit('-', 1)[1]))
    return instances_dict


def _install_load_balancer(instances_dict, key_path):
    logging.info('Installing load balancer')
    load_balancer = instances_dict['load_balancer'][0]
    managers_details = ''
    scp_local_to_remote(key_path, load_balancer, LOCAL_INSTALL_CLUSTER_CERTS,
                        REMOTE_PARENT_DIRECTORY)
    scp_local_to_remote(key_path, load_balancer, 'install_load_balancer.sh',
                        REMOTE_PARENT_DIRECTORY)
    for manager in instances_dict['manager']:
        managers_details += (manager.private_ip + ' ' +
                             manager.public_ip + ' ')
    install_command = 'sudo bash {script_path} {managers_details} {directory}' \
        .format(script_path=os.path.join(REMOTE_PARENT_DIRECTORY,
                                         'install_load_balancer.sh'),
                managers_details=managers_details,
                directory=REMOTE_PARENT_DIRECTORY)
    stdin, stdout, stderr = load_balancer.exec_command(install_command)
    print(stdout.read())
    return


def _create_install_cluster_directory(license_path, download_link):
    logging.info('Creating `install_cluster` directory')
    os.system('rm -rf {}_old'.format(LOCAL_INSTALL_CLUSTER))
    if os.path.exists(LOCAL_INSTALL_CLUSTER):
        os.system('mv {0} {0}_old'.format(LOCAL_INSTALL_CLUSTER))
    os.mkdir(LOCAL_INSTALL_CLUSTER)
    os.mkdir(LOCAL_INSTALL_CLUSTER + '/certs')
    _download_manager_and_create_license(license_path, download_link)


def _parse_command():
    parser = argparse.ArgumentParser(description='Installing an Active-Active '
                                                 'manager cluster')
    parser.add_argument('--config-path', action='store', type=str,
                        required=True, help='The config_env.yaml file path')
    parser.add_argument('--clean-on-failure', dest='clean',
                        action='store_true', default=False,
                        help='Pass this flag if you want to clean your '
                             'Openstack environment on failure')
    return parser.parse_args()


def _delete_factory_vm_from_openstack_env(connection, environment_ids_dict):
    delete_vm(connection, environment_ids_dict['factory'])
    del environment_ids_dict['factory']


def _show_successful_installation_message(start_time, end_time):
    logging.info('Successfully installed an Active-Active cluster in %.2f'
                 ' minutes', ((end_time - start_time) / 60))
    time.sleep(0.5)


def _show_load_balancer_ip(load_balancer_ip):
    logging.info('In order to connect to the load balancer, use the ip {}'.
                 format(load_balancer_ip))


def _show_manager_ips(manager_nodes):
    managers_str = ''
    for manager in manager_nodes:
        managers_str += '{0}: {1}\n'.format(manager.name, manager.public_ip)
    logging.info('In order to connect to one of the managers, use one of the '
                 'following IPs:\n{}'.format(managers_str))


def main():
    parse_args = _parse_command()
    clean_openstack_env = parse_args.clean
    logging.basicConfig(level=logging.INFO)
    start_time = time.time()
    connected_to_openstack = False
    with open(parse_args.config_path) as config_file:
        config = yaml.load(config_file, yaml.Loader)
    instances_raw_dict, connection, environment_ids_dict = \
        create_openstack_vms(config, logging, clean_openstack_env)
    try:
        key_path = config['key_file_path']
        vm_username = config['machine_username']
        download_link = config['manager_rpm_download_link']
        rpm_name = config['manager_rpm_name']
        using_load_balancer = config['using_load_balancer']
        _create_install_cluster_directory(config['cloudify_license_path'],
                                          download_link)
        instances_dict = _get_instances_dict(instances_raw_dict, key_path,
                                             vm_username)
        clients_list = [server.client for server in _create_instances_list(
            instances_dict, using_load_balancer)]
        connected_to_openstack = True
        _generate_certs(instances_dict, key_path, download_link, rpm_name)
        _delete_factory_vm_from_openstack_env(connection, environment_ids_dict)
        rabbitmq_cred = _prepare_postgres_rabbit_config_files(instances_dict)
        _install_instances(instances_dict, key_path, rpm_name, rabbitmq_cred)
        _configure_status_reporter(instances_dict)
        if using_load_balancer:
            _install_load_balancer(instances_dict, key_path)
            time.sleep(0.5)
            _show_load_balancer_ip(instances_dict['load_balancer'][0].public_ip)
        _show_manager_ips(instances_dict['manager'])
        _close_clients_connection(clients_list)
        end_time = time.time()
        _show_successful_installation_message(start_time, end_time)
    except Exception:
        if connected_to_openstack:
            _close_clients_connection(clients_list)
        handle_failure(connection, environment_ids_dict, clean_openstack_env,
                       logging)


if __name__ == "__main__":
    main()