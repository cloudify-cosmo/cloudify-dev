#! /usr/bin/env python
import yaml
import logging
import argparse
from openstack_connection import clean_openstack, create_connection


def _parse_command():
    parser = argparse.ArgumentParser(description='Cleaning the OpenStack '
                                                 'environment')
    parser.add_argument('--config-path', action='store', type=str,
                        required=True, help='The config_env.yaml file path')
    parser.add_argument('--environment-ids-path', action='store', required=True,
                        type=str, help='The environment_ids.yaml file path. '
                                       'These servers and security group '
                                       'will be deleted')
    return parser.parse_args().config_path, \
           parser.parse_args().environment_ids_path


def main():
    config_path, environment_ids_path = _parse_command()
    with open(config_path) as config_file:
        config = yaml.load(config_file, yaml.Loader)
    connection = create_connection(config)
    with open(environment_ids_path, 'r') as f:
        environment_ids_dict = yaml.load(f, yaml.Loader)
    logging.basicConfig(level=logging.INFO)
    clean_openstack(connection, environment_ids_dict, logging)


if __name__ == "__main__":
    main()
