#! /usr/bin/env python
from os.path import dirname, exists

import yaml
import logging
import argparse

from instances_connection import (logger,
                                  ReplaceCertificatesConfig,
                                  ReplaceCertificatesError)


def get_dict_from_yaml(yaml_path):
    with open(yaml_path) as f:
        yaml_dict = yaml.load(f, yaml.Loader)
    return yaml_dict


def raise_errors_list(errors_list):
    logger.info(_errors_list_str(errors_list))
    raise ReplaceCertificatesError()


def _errors_list_str(errors_list):
    err_str = 'Errors:\n'
    err_lst = '\n'.join([' [{0}] {1}'.format(i+1, err) for i, err
                         in enumerate(errors_list)])
    return err_str + err_lst


def validate_config_dict(config_dict):
    errors_list = []
    _validate_instances(errors_list, config_dict)
    _check_path(errors_list, config_dict['manager']['new_ldap_ca_cert'])
    if errors_list:
        raise_errors_list(errors_list)


def _assert_username_and_key_file_path(config_dict, errors_list):
    if ((not config_dict.get('username')) or
            (not config_dict.get('key_file_path'))):
        errors_list.append('Please provide the username and key_file_path')

    if not exists(config_dict.get('key_file_path')):
        errors_list.append('The key_file_path does not exist')


def _validate_instances(errors_list, config_dict):
    for instance in 'postgresql_server', 'rabbitmq':
        _validate_cert_and_key(errors_list,
                               config_dict[instance]['cluster_members'])
        _validate_new_ca_cert(errors_list, config_dict, instance)

    _validate_manager_cert_and_key(errors_list,
                                   config_dict['manager']['cluster_members'])
    _validate_new_manager_ca_certs(errors_list, config_dict)


def _validate_new_ca_cert(errors_list, config_dict, instance_name):
    _validate_ca_cert(errors_list, config_dict[instance_name], instance_name,
                      'new_ca_cert', 'new_cert',
                      config_dict[instance_name]['cluster_members'])


def _validate_new_manager_ca_certs(errors_list, config_dict):
    _validate_ca_cert(errors_list, config_dict['manager'], 'manager',
                      'new_ca_cert', 'new_internal_cert',
                      config_dict['manager']['cluster_members'])
    _validate_ca_cert(errors_list, config_dict['manager'],
                      'manager', 'new_external_ca_cert',
                      'new_external_cert',
                      config_dict['manager']['cluster_members'])
    _validate_ca_cert(errors_list, config_dict['postgresql_server'],
                      'postgresql_server', 'new_ca_cert',
                      'new_postgresql_client_cert',
                      config_dict['manager']['cluster_members'])


def _validate_ca_cert(errors_list, instance, instance_name, new_ca_cert_name,
                      cert_name, cluster_members):
    """Validates the CA cert.

    Validates that the CA path is valid, and if it is, then a new cert was
    specified for all cluster members.
    """
    err_msg = '{0} was specified for instance {1}, but {2} was not specified' \
              ' for all cluster members.'.format(new_ca_cert_name,
                                                 instance_name,
                                                 cert_name)

    new_ca_cert_path = instance.get(new_ca_cert_name)
    if _check_path(errors_list, new_ca_cert_path):
        if not all(member.get(cert_name) for member in cluster_members):
            errors_list.append(err_msg)


def _validate_cert_and_key(errors_list, nodes):
    for node in nodes:
        _validate_node_certs(errors_list, node, 'new_cert', 'new_key')


def _validate_manager_cert_and_key(errors_list, nodes):
    for node in nodes:
        _validate_node_certs(errors_list, node,
                             'new_internal_cert',
                             'new_internal_key')
        _validate_node_certs(errors_list, node,
                             'new_external_cert',
                             'new_external_key')
        _validate_node_certs(errors_list, node,
                             'new_postgresql_client_cert',
                             'new_postgresql_client_key')


def _validate_node_certs(errors_list, certs_dict, new_cert_name, new_key_name):
    new_cert_path = certs_dict.get(new_cert_name)
    new_key_path = certs_dict.get(new_key_name)
    if bool(new_key_path) != bool(new_cert_path):
        errors_list.append('Either both {0} and {1} must be '
                           'provided, or neither for host '
                           '{2}'.format(new_cert_name, new_key_name,
                                        certs_dict['host_ip']))
    _check_path(errors_list, new_cert_path)
    _check_path(errors_list, new_key_path)


def _check_path(errors_list, path):
    if path:
        if exists(path):
            return True
        errors_list.append('The path {0} does not exist'.format(path))
    return False


def parse_command():
    parser = argparse.ArgumentParser(description='Replacing certificates on '
                                                 'a cluster')
    parser.add_argument('--config-path', action='store', type=str,
                        default='{0}/replace_certificates_config.yaml'.format(
                            dirname(__file__)),
                        help='The replace_certificates_config.yaml file path')
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        dest='verbose')
    return parser.parse_args()


def main():
    parse_args = parse_command()
    verbose = parse_args.verbose
    if verbose:
        logger.setLevel(logging.DEBUG)
    config_dict = get_dict_from_yaml(parse_args.config_path)
    validate_config_dict(config_dict)
    main_config = ReplaceCertificatesConfig(config_dict, verbose)
    main_config.validate_certificates()
    main_config.replace_certificates()


if __name__ == '__main__':
    main()
