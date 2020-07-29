#! /usr/bin/env python
import os
import sys
import csv
import time
import json
import shlex
import socket
import base64
import urllib2
import logging
import argparse
import collections
from tempfile import mkstemp
from contextlib import contextmanager
from getpass import getuser
from os.path import isfile
import pwd
import subprocess

import requests
from retrying import retry
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from ruamel.yaml.comments import CommentedMap

yaml = YAML()

LOG_FILE_PATH = '{0}/replace_certificates.log'.format(
    os.path.dirname(__file__))


def init_logger():
    log = logging.getLogger('Replacing-Certificates')
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler(LOG_FILE_PATH)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)
    log.addHandler(stdout_handler)
    log.addHandler(file_handler)
    return log


logger = init_logger()


SERVICES_TO_INSTALL = 'services_to_install'

DATABASE_SERVICE = 'database_service'
QUEUE_SERVICE = 'queue_service'
MANAGER_SERVICE = 'manager_service'

NGINX = 'nginx'
STAGE = 'stage'
COMPOSER = 'composer'

CLOUDIFY_HOME_DIR = '/etc/cloudify'
USER_CONFIG_PATH = os.path.join(CLOUDIFY_HOME_DIR, 'config.yaml')

REST_HOME_DIR = '/opt/manager'
REST_CONFIG_PATH = os.path.join(REST_HOME_DIR, 'cloudify-rest.conf')
REST_SECURITY_CONFIG_PATH = os.path.join(REST_HOME_DIR, 'rest-security.conf')
REST_AUTHORIZATION_CONFIG_PATH = os.path.join(REST_HOME_DIR,
                                              'authorization.conf')

ETCD_SERVER_CERT_PATH = '/etc/etcd/etcd.crt'
ETCD_SERVER_KEY_PATH = '/etc/etcd/etcd.key'
ETCD_CA_PATH = '/etc/etcd/ca.crt'
PATRONI_REST_CERT_PATH = '/var/lib/patroni/rest.crt'
PATRONI_REST_KEY_PATH = '/var/lib/patroni/rest.key'
PATRONI_DB_CERT_PATH = '/var/lib/patroni/db.crt'
PATRONI_DB_KEY_PATH = '/var/lib/patroni/db.key'
PATRONI_DB_CA_PATH = '/var/lib/patroni/ca.crt'
PG_CONF_PATH = '/var/lib/pgsql/9.5/data/cloudify-postgresql.conf'
PG_CA_CERT_PATH = os.path.join(os.path.dirname(PG_CONF_PATH), 'root.crt')
PG_SERVER_CERT_PATH = os.path.join(os.path.dirname(PG_CONF_PATH), 'server.crt')
PG_SERVER_KEY_PATH = os.path.join(os.path.dirname(PG_CONF_PATH), 'server.key')

BROKER_CERT_LOCATION = '/etc/cloudify/ssl/rabbitmq-cert.pem'
BROKER_KEY_LOCATION = '/etc/cloudify/ssl/rabbitmq-key.pem'
BROKER_CA_LOCATION = '/etc/cloudify/ssl/rabbitmq-ca.pem'

POSTGRESQL_CLIENT_CERT_FILENAME = 'postgresql.crt'
POSTGRESQL_CLIENT_KEY_FILENAME = 'postgresql.key'
POSTGRESQL_CA_CERT_FILENAME = 'postgresql_ca.crt'
SSL_CERTS_TARGET_DIR = os.path.join(CLOUDIFY_HOME_DIR, 'ssl')
POSTGRESQL_CLIENT_CERT_PATH = \
    os.path.join(SSL_CERTS_TARGET_DIR, POSTGRESQL_CLIENT_CERT_FILENAME)
POSTGRESQL_CLIENT_KEY_PATH = \
    os.path.join(SSL_CERTS_TARGET_DIR, POSTGRESQL_CLIENT_KEY_FILENAME)
POSTGRESQL_CA_CERT_PATH = \
    os.path.join(SSL_CERTS_TARGET_DIR, POSTGRESQL_CA_CERT_FILENAME)

LDAP_CA_CERT_PATH = '/etc/cloudify/ssl/ldap_ca.crt'

INTERNAL_CERT_FILENAME = 'cloudify_internal_cert.pem'
INTERNAL_KEY_FILENAME = 'cloudify_internal_key.pem'
CA_CERT_FILENAME = 'cloudify_internal_ca_cert.pem'
CA_KEY_FILENAME = 'cloudify_internal_ca_key.pem'
EXTERNAL_CA_CERT_FILENAME = 'cloudify_external_ca_cert.pem'
EXTERNAL_CERT_FILENAME = 'cloudify_external_cert.pem'
EXTERNAL_KEY_FILENAME = 'cloudify_external_key.pem'
INTERNAL_CERT_PATH = os.path.join(SSL_CERTS_TARGET_DIR, INTERNAL_CERT_FILENAME)
INTERNAL_KEY_PATH = os.path.join(SSL_CERTS_TARGET_DIR, INTERNAL_KEY_FILENAME)
CA_CERT_PATH = os.path.join(SSL_CERTS_TARGET_DIR, CA_CERT_FILENAME)
CA_KEY_PATH = os.path.join(SSL_CERTS_TARGET_DIR, CA_KEY_FILENAME)
EXTERNAL_CA_CERT_PATH = os.path.join(SSL_CERTS_TARGET_DIR,
                                     EXTERNAL_CA_CERT_FILENAME)
EXTERNAL_CERT_PATH = os.path.join(SSL_CERTS_TARGET_DIR, EXTERNAL_CERT_FILENAME)
EXTERNAL_KEY_PATH = os.path.join(SSL_CERTS_TARGET_DIR, EXTERNAL_KEY_FILENAME)

STAGE_HOME_DIR = os.path.join('/opt', 'cloudify-{0}'.format(STAGE))
STAGE_CONF_DIR = os.path.join(STAGE_HOME_DIR, 'conf')
STAGE_DB_CLIENT_KEY_PATH = '/etc/cloudify/ssl/stage_db.key'
STAGE_DB_CLIENT_CERT_PATH = '/etc/cloudify/ssl/stage_db.crt'
STAGE_DB_CA_PATH = os.path.join(STAGE_CONF_DIR, 'db_ca.crt')

COMPOSER_HOME_DIR = os.path.join('/opt', 'cloudify-{0}'.format(COMPOSER))
COMPOSER_CONF_DIR = os.path.join(COMPOSER_HOME_DIR, 'backend', 'conf')
COMPOSER_DB_CLIENT_KEY_PATH = '/etc/cloudify/ssl/composer_db.key'
COMPOSER_DB_CLIENT_CERT_PATH = '/etc/cloudify/ssl/composer_db.crt'
COMPOSER_DB_CA_PATH = os.path.join(COMPOSER_CONF_DIR, 'db_ca.crt')
COMPOSER_USER = '{0}_user'.format(COMPOSER)
COMPOSER_GROUP = '{0}_group'.format(COMPOSER)
COMPOSER_PORT = 3000

ETCD_USER = 'etcd'
ETCD_GROUP = 'etcd'

STAGE_USER = '{0}_user'.format(STAGE)
STAGE_GROUP = '{0}_group'.format(STAGE)

POSTGRES_USER = POSTGRES_GROUP = 'postgres'
POSTGRESQL_SERVER = 'postgresql_server'
POSTGRESQL_CLIENT = 'postgresql_client'
RABBITMQ = 'rabbitmq'
MANAGER = 'manager'
RESTSERVICE = 'restservice'
HOSTNAME = 'hostname'

SSL_ENABLED = 'ssl_enabled'
SSL_CLIENT_VERIFICATION = 'ssl_client_verification'
CLOUDIFY_USER = 'cfyuser'
CLOUDIFY_GROUP = 'cfyuser'
SSL_INPUTS = 'ssl_inputs'
REST_URL = 'http://127.0.0.1:{port}/api/v3.1/{endpoint}'

NEW_CERTS_TMP_DIR_PATH = '/tmp/new_cloudify_certs/'

NEW_BROKER_CERT_FILE_PATH = NEW_CERTS_TMP_DIR_PATH + 'new_rabbitmq_cert.pem'
NEW_BROKER_KEY_FILE_PATH = NEW_CERTS_TMP_DIR_PATH + 'new_rabbitmq_key.pem'
NEW_BROKER_CA_CERT_FILE_PATH = (NEW_CERTS_TMP_DIR_PATH +
                                'new_rabbitmq_ca_cert.pem')

NEW_POSTGRESQL_CERT_FILE_PATH = (NEW_CERTS_TMP_DIR_PATH +
                                 'new_postgresql_server_cert.pem')
NEW_POSTGRESQL_KEY_FILE_PATH = (NEW_CERTS_TMP_DIR_PATH +
                                'new_postgresql_server_key.pem')
NEW_POSTGRESQL_CLIENT_CERT_FILE_PATH = (NEW_CERTS_TMP_DIR_PATH +
                                        'new_postgresql_client_cert.pem')
NEW_POSTGRESQL_CLIENT_KEY_FILE_PATH = (NEW_CERTS_TMP_DIR_PATH +
                                       'new_postgresql_client_key.pem')
NEW_POSTGRESQL_CA_CERT_FILE_PATH = (NEW_CERTS_TMP_DIR_PATH +
                                    'new_postgresql_server_ca_cert.pem')

NEW_INTERNAL_CERT_FILE_PATH = NEW_CERTS_TMP_DIR_PATH + 'new_internal_cert.pem'
NEW_INTERNAL_KEY_FILE_PATH = NEW_CERTS_TMP_DIR_PATH + 'new_internal_key.pem'
NEW_INTERNAL_CA_CERT_FILE_PATH = (NEW_CERTS_TMP_DIR_PATH + 'new_ca_cert.pem')

NEW_EXTERNAL_CERT_FILE_PATH = NEW_CERTS_TMP_DIR_PATH + 'new_external_cert.pem'
NEW_EXTERNAL_KEY_FILE_PATH = NEW_CERTS_TMP_DIR_PATH + 'new_external_key.pem'
NEW_EXTERNAL_CA_CERT_FILE_PATH = (NEW_CERTS_TMP_DIR_PATH +
                                  'new_external_ca_cert.pem')

NEW_LDAP_CA_CERT_PATH = (NEW_CERTS_TMP_DIR_PATH + 'new_ldap_ca_cert.pem')


class ReplaceCertificatesError(StandardError):
    pass


class ValidationError(ReplaceCertificatesError):
    pass


class InputError(ReplaceCertificatesError):
    pass


class NetworkError(ReplaceCertificatesError):
    pass


class FileError(ReplaceCertificatesError):
    pass


class ProcessExecutionError(StandardError):
    def __init__(self, message, return_code=None):
        self.return_code = return_code
        super(ProcessExecutionError, self).__init__(message)


def dict_merge(dct, merge_dct):
    """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    Taken from: https://gist.github.com/angstwad/bf22d1822c38a92ec0a9
    :param dct: dict onto which the merge is executed
    :param merge_dct: dct merged into dct
    :return: None
    """
    for k, v in merge_dct.items():
        if (k in dct and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], collections.Mapping)):
            dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]


class Config(CommentedMap):
    TEMP_PATHS = 'temp_paths_to_remove'

    def _load_user_config(self):
        # Allow `config.yaml` not to exist - this is normal for teardown
        if isfile(USER_CONFIG_PATH):
            # Override any default values with values from config.yaml
            user_config = self._load_yaml(USER_CONFIG_PATH)
            dict_merge(self, user_config)

    @contextmanager
    def _own_config_file(self):
        try:
            # Not using common module because of circular import issues
            subprocess.check_call([
                'sudo', 'chown', getuser() + '.', USER_CONFIG_PATH
            ])
            yield
        finally:
            try:
                pwd.getpwnam('cfyuser')
                subprocess.check_call([
                    'sudo', 'chown', CLOUDIFY_USER + '.', USER_CONFIG_PATH
                ])
            except KeyError:
                # No cfyuser, don't pass ownnership back (this is probably a
                # DB or rabbit node)
                pass

    def _load_yaml(self, path_to_yaml):
        try:
            with self._own_config_file():
                with open(path_to_yaml, 'r') as f:
                    return yaml.load(f)
        except YAMLError as e:
            raise InputError(
                'User config file {0} is not a properly formatted '
                'YAML file:\n{1}'.format(path_to_yaml, e)
            )
        except IOError as e:
            raise RuntimeError(
                'Cannot access {config}: {error}'.format(
                    config=path_to_yaml,
                    error=e
                )
            )

    def load_config(self):
        self._load_user_config()

    def add_temp_path_to_clean(self, new_path_to_remove):
        paths_to_remove = self.setdefault(self.TEMP_PATHS, [])
        paths_to_remove.append(new_path_to_remove)


config = Config()


def run(command, retries=0, stdin=b'', ignore_failures=False, stdout=None,
        env=None):
    if isinstance(command, str):
        command = shlex.split(command)
    stderr = subprocess.PIPE
    stdout = stdout or subprocess.PIPE

    logger.debug('Running: {0}'.format(command))
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout,
                            stderr=stderr, env=env)
    proc.aggr_stdout, proc.aggr_stderr = proc.communicate(input=stdin)
    if proc.returncode != 0:
        if retries:
            logger.warn('Failed running command: %s. Retrying. '
                        '(%s left)', command, retries)
            proc = run(command, retries - 1)
        elif not ignore_failures:
            msg = 'Failed running command: {0} ({1}).'.format(
                command, proc.aggr_stderr)
            raise ProcessExecutionError(msg, proc.returncode)
    return proc


def sudo(command, *args, **kwargs):
    if isinstance(command, str):
        command = shlex.split(command)
    if 'env' in kwargs:
        command = ['sudo', '-E'] + command
    else:
        command.insert(0, 'sudo')
    return run(command=command, *args, **kwargs)


class SystemD(object):
    @staticmethod
    def systemctl(action, service='', retries=0, ignore_failure=False):
        systemctl_cmd = ['systemctl', action]
        if service:
            systemctl_cmd.append(service)
        return sudo(systemctl_cmd, retries=retries,
                    ignore_failures=ignore_failure)

    @staticmethod
    def _get_full_service_name(service_name, append_prefix):
        if append_prefix:
            return 'cloudify-{0}'.format(service_name)
        return service_name

    def restart(self,
                service_name,
                retries=0,
                ignore_failure=False,
                append_prefix=True):
        full_service_name = self._get_full_service_name(service_name,
                                                        append_prefix)
        self.systemctl('restart', full_service_name, retries,
                       ignore_failure=ignore_failure)

    def is_alive(self, service_name, append_prefix=True):
        service_name = self._get_full_service_name(service_name, append_prefix)
        result = self.systemctl('status', service_name, ignore_failure=True)
        return result.returncode == 0

    @retry(stop_max_attempt_number=3, wait_fixed=1000)
    def verify_alive(self, service_name, append_prefix=True):
        if self.is_alive(service_name, append_prefix):
            logger.debug('{0} is running'.format(service_name))
        else:
            raise ValidationError('{0} is not running'.format(service_name))


systemd = SystemD()


def ensure_destination_dir_exists(destination):
    destination_dir = os.path.dirname(destination)
    if not os.path.exists(destination_dir):
        sudo(['mkdir', '-p', destination_dir])


def copy(source, destination, backup=False):
    if os.path.exists(destination):
        if backup:
            modified_name = time.strftime('%Y%m%d-%H%M%S_') + \
                            os.path.basename(destination)
            new_dest = os.path.join(os.path.dirname(destination),
                                    modified_name)
            sudo(['cp', '-rp', destination, new_dest])
    else:
        ensure_destination_dir_exists(destination)
    sudo(['cp', '-rp', source, destination])


def write_to_tempfile(contents, json_dump=False, cleanup=True):
    fd, file_path = mkstemp()
    os.close(fd)
    if json_dump:
        contents = json.dumps(contents)

    with open(file_path, 'w') as f:
        f.write(contents)

    if cleanup:
        config.add_temp_path_to_clean(file_path)
    return file_path


def is_port_open(port, host='localhost'):
    """Try to connect to (host, port), return if the port was listening."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    return sock.connect_ex((host, port)) == 0


def wait_for_port(port, host='localhost'):
    """Helper function to wait for a port to open before continuing"""
    counter = 1

    logger.info('Waiting for {0}:{1} to become available...'.format(
        host, port))

    for tries in range(24):
        if not is_port_open(port, host=host):
            logger.info(
                '{0}:{1} is not available yet, retrying... '
                '({2}/24)'.format(host, port, counter))
            time.sleep(2)
            counter += 1
            continue
        logger.info('{0}:{1} is open!'.format(host, port))
        return
    raise NetworkError(
        'Failed to connect to {0}:{1}...'.format(host, port)
    )


def get_auth_headers():
    security = config[MANAGER]['security']
    username = security['admin_username']
    password = security['admin_password']
    return {
        'Authorization': 'Basic ' + base64.b64encode('{0}:{1}'.format(
            username, password)
        ),
        'tenant': 'default_tenant'
    }


def remove_key_encryption(src_key_path,
                          dst_key_path,
                          key_password):
    sudo([
        'openssl', 'rsa',
        '-in', src_key_path,
        '-out', dst_key_path,
        '-passin', u'pass:{0}'.format(key_password).encode('utf-8')
    ])


def _check_ssl_file(filename, kind='Key', password=None):
    """Does the cert/key file exist and is it valid?"""
    file_exists_check = sudo(['test', '-f', filename], ignore_failures=True)
    if file_exists_check.returncode != 0:
        raise ValidationError(
            '{0} file {1} does not exist'
            .format(kind, filename))
    if kind == 'Key':
        check_command = ['openssl', 'rsa', '-in', filename, '-check', '-noout']
        if password:
            check_command += [
                '-passin',
                u'pass:{0}'.format(password).encode('utf-8')
            ]
    elif kind == 'Cert':
        check_command = ['openssl', 'x509', '-in', filename, '-noout']
    else:
        raise ValueError('Unknown kind: {0}'.format(kind))
    proc = sudo(check_command, ignore_failures=True)
    if proc.returncode != 0:
        password_err = ''
        if password:
            password_err = ' (or the provided password is incorrect)'
        raise ValidationError('{0} file {1} is invalid{2}'
                              .format(kind, filename, password_err))


def _check_signed_by(ca_filename, cert_filename):
    ca_check_command = [
        'openssl', 'verify', '-CAfile', ca_filename, cert_filename
    ]
    try:
        sudo(ca_check_command)
    except subprocess.CalledProcessError:
        raise ValidationError(
            'Provided certificate {cert} was not signed by provided '
            'CA {ca}'.format(
                cert=cert_filename,
                ca=ca_filename,
            )
        )


def _check_cert_key_match(cert_filename, key_filename, password=None):
    _check_ssl_file(key_filename, kind='Key', password=password)
    _check_ssl_file(cert_filename, kind='Cert')
    key_modulus_command = ['openssl', 'rsa', '-noout', '-modulus',
                           '-in', key_filename]
    if password:
        key_modulus_command += [
            '-passin',
            u'pass:{0}'.format(password).encode('utf-8')
        ]
    cert_modulus_command = ['openssl', 'x509', '-noout', '-modulus',
                            '-in', cert_filename]
    key_modulus = sudo(key_modulus_command).aggr_stdout.strip()
    cert_modulus = sudo(cert_modulus_command).aggr_stdout.strip()
    if cert_modulus != key_modulus:
        raise ValidationError(
            'Key {key_path} does not match the cert {cert_path}'.format(
                key_path=key_filename,
                cert_path=cert_filename,
            )
        )


def check_certificates(config_section, section_path,
                       cert_path='cert_path', key_path='key_path',
                       ca_path='ca_path', key_password='key_password',
                       require_non_ca_certs=True):
    """Check that the provided cert, key, and CA actually match"""
    cert_filename = config_section.get(cert_path)
    key_filename = config_section.get(key_path)

    ca_filename = config_section.get(ca_path)
    password = config_section.get(key_password)

    if not cert_filename and not key_filename and require_non_ca_certs:
        failing = []
        if password:
            failing.append('key_password')
        if ca_filename:
            failing.append('ca_path')
        if failing:
            failing = ' or '.join(failing)
            raise ValidationError(
                'If {failing} was provided, both cert_path and key_path '
                'must be provided in {component}'.format(
                    failing=failing,
                    component=section_path,
                )
            )

    validate_certificates(cert_filename, key_filename, ca_filename, password)
    return cert_filename, key_filename, ca_filename, password


def validate_certificates(cert_filename=None, key_filename=None,
                          ca_filename=None, password=None):
    if cert_filename and key_filename:
        _check_cert_key_match(cert_filename, key_filename, password)
    elif cert_filename or key_filename:
        raise ValidationError('Either both cert_path and key_path must be '
                              'provided, or neither.')

    if ca_filename:
        _check_ssl_file(ca_filename, kind='Cert')
        if cert_filename:
            _check_signed_by(ca_filename, cert_filename)


def use_supplied_certificates(component_name,
                              cert_destination=None,
                              key_destination=None,
                              ca_destination=None,
                              owner=CLOUDIFY_USER,
                              group=CLOUDIFY_GROUP,
                              key_perms='440',
                              cert_perms='444',
                              prefix='',
                              just_ca_cert=False,
                              sub_component=None,
                              validate_certs_src_exist=False):
    """Use user-supplied certificates, checking they're not broken.

    Any private key password will be removed, and the config will be
    updated after the certificates are moved to the intended destination.

    At least one of the cert_, key_, or ca_ destination entries must be
    provided.

    Returns True if supplied certificates were used.
    """
    key_path = prefix + 'key_path'
    cert_path = prefix + 'cert_path'
    ca_path = prefix + 'ca_path'
    key_password = prefix + 'key_password'

    # The ssl_inputs has different names for some of the certificates
    if component_name == SSL_INPUTS:
        if prefix == 'internal_':
            ca_path = 'ca_cert_path'
            key_password = 'ca_key_password'
        elif prefix == 'external_':
            ca_path = prefix + 'ca_cert_path'

    if just_ca_cert:
        ca_path = cert_path
        key_path = None
        cert_path = None

    config_section = config[component_name]
    section_path = component_name
    if sub_component:
        config_section = config_section[sub_component]
        section_path = section_path + '.' + sub_component

    cert_src, key_src, ca_src, key_pass = check_certificates(
        config_section,
        section_path,
        cert_path=cert_path,
        key_path=key_path,
        ca_path=ca_path,
        key_password=key_password,
        require_non_ca_certs=False,
    )

    if not any([cert_src, key_src, ca_src, key_pass]):
        # No certificates supplied, so not using them
        logger.debug('No user-supplied certificates were present.')
        return False

    if validate_certs_src_exist and not (cert_src and key_src):
        logger.debug('The certificate and key were not provided.')
        return False

    # Put the files in the correct place
    logger.info('Ensuring files are in correct locations.')

    if cert_destination and cert_src != cert_destination:
        copy(cert_src, cert_destination, True)
    if key_destination and key_src != key_destination:
        copy(key_src, key_destination, True)
    if ca_destination and ca_src != ca_destination:
        if ca_src:
            copy(ca_src, ca_destination, True)
        else:
            copy(cert_destination, ca_destination, True)

    if key_pass:
        remove_key_encryption(
            key_destination, key_destination, key_pass
        )

    logger.info('Setting certificate ownership and permissions.')

    for path in cert_destination, key_destination, ca_destination:
        if path:
            sudo(['chown', '{owner}.{group}'.format(owner=owner, group=group),
                  path])
    # Make key only readable by user and group
    if key_destination:
        sudo(['chmod', key_perms, key_destination])
    # Make certs readable by anyone
    for path in cert_destination, ca_destination:
        if path:
            sudo(['chmod', cert_perms, path])

    # Supplied certificates were used
    return True


def get_and_validate_certs_for_replacement(
        default_cert_location,
        default_key_location,
        default_ca_location,
        new_cert_location,
        new_key_location,
        new_ca_location):
    """Validates the new certificates for replacement.

    This function validates the new specified certificates for replacement,
    based on the new certificates specified and the current ones. E.g. if
    onlt a new certificate and key were specified, then it will validate them
    with the current CA.
    """

    cert_filename, key_filename = get_cert_and_key_filenames(
        new_cert_location, new_key_location,
        default_cert_location, default_key_location)

    ca_filename = get_ca_filename(new_ca_location, default_ca_location)

    validate_certificates(cert_filename, key_filename, ca_filename)
    return cert_filename, key_filename, ca_filename


def get_cert_and_key_filenames(new_cert_location,
                               new_key_location,
                               default_cert_location,
                               default_key_location):
    if os.path.exists(new_cert_location):
        return new_cert_location, new_key_location

    return default_cert_location, default_key_location


def get_ca_filename(new_ca_location, default_ca_location):
    return (new_ca_location if os.path.exists(new_ca_location)
            else default_ca_location)


class BaseComponent(object):
    def replace_certificates(self):
        pass

    def validate_new_certs(self):
        pass


class PostgresqlServer(BaseComponent):
    component_name = 'postgresql_server'

    def handle_cluster_certificates(self):
        etcd_certs_config = {
            'component_name': self.component_name,
            'cert_destination': ETCD_SERVER_CERT_PATH,
            'key_destination': ETCD_SERVER_KEY_PATH,
            'ca_destination': ETCD_CA_PATH,
            'owner': ETCD_USER,
            'group': ETCD_GROUP,
            'key_perms': '400',
            'cert_perms': '444'
        }

        patroni_rest_certs_config = {
            'component_name': self.component_name,
            'cert_destination': PATRONI_REST_CERT_PATH,
            'key_destination': PATRONI_REST_KEY_PATH,
            'owner': POSTGRES_USER,
            'group': POSTGRES_GROUP,
            'key_perms': '400',
            'cert_perms': '444'
        }

        patroni_db_certs_config = {
            'component_name': self.component_name,
            'cert_destination': PATRONI_DB_CERT_PATH,
            'key_destination': PATRONI_DB_KEY_PATH,
            'ca_destination': PATRONI_DB_CA_PATH,
            'owner': POSTGRES_USER,
            'group': POSTGRES_GROUP,
            'key_perms': '400',
            'cert_perms': '444'
        }

        for cert_config in [etcd_certs_config,
                            patroni_rest_certs_config,
                            patroni_db_certs_config]:
            use_supplied_certificates(**cert_config)

    def replace_certificates(self):
        if (os.path.exists(NEW_POSTGRESQL_CERT_FILE_PATH) or
                os.path.exists(NEW_POSTGRESQL_CA_CERT_FILE_PATH)):
            self.log_replacing_certificates()
            self._write_certs_to_config()
            if config[POSTGRESQL_SERVER]['cluster']['nodes']:  # cluster case
                self.handle_cluster_certificates()
                self._restart_etcd()
                systemd.restart('patroni', append_prefix=False)
                systemd.verify_alive('patroni', append_prefix=False)

    def _restart_etcd(self):
        logger.info('Restarting etcd')
        systemd.restart('etcd', append_prefix=False, ignore_failure=True)
        self._wait_for_etcd()
        logger.info('etcd has restarted')

    @staticmethod
    def _etcd_is_running():
        status = run(['systemctl', 'is-active', 'etcd'],
                     ignore_failures=True).aggr_stdout.strip()
        return status in ('active', 'activating')

    def _wait_for_etcd(self):
        while not self._etcd_is_running():
            logger.info('Waiting for etcd to start...')
            time.sleep(1)

    @staticmethod
    def _write_certs_to_config():
        if os.path.exists(NEW_POSTGRESQL_CERT_FILE_PATH):
            config[POSTGRESQL_SERVER]['cert_path'] = \
                NEW_POSTGRESQL_CERT_FILE_PATH
            config[POSTGRESQL_SERVER]['key_path'] = \
                NEW_POSTGRESQL_KEY_FILE_PATH
        if os.path.exists(NEW_POSTGRESQL_CA_CERT_FILE_PATH):
            config[POSTGRESQL_SERVER]['ca_path'] = \
                NEW_POSTGRESQL_CA_CERT_FILE_PATH

    def validate_new_certs(self):
        get_and_validate_certs_for_replacement(
            default_cert_location=ETCD_SERVER_CERT_PATH,
            default_key_location=ETCD_SERVER_KEY_PATH,
            default_ca_location=ETCD_CA_PATH,
            new_cert_location=NEW_POSTGRESQL_CERT_FILE_PATH,
            new_key_location=NEW_POSTGRESQL_KEY_FILE_PATH,
            new_ca_location=NEW_POSTGRESQL_CA_CERT_FILE_PATH
        )

    def log_replacing_certificates(self):
        logger.info(
            'Replacing certificates on the postgresql_server component')


class RabbitMQ(BaseComponent):
    @staticmethod
    def handle_certificates():
        cert_config = {
            'component_name': 'rabbitmq',
            'cert_destination': BROKER_CERT_LOCATION,
            'key_destination': BROKER_KEY_LOCATION,
            'ca_destination': BROKER_CA_LOCATION,
            'owner': 'rabbitmq',
            'group': 'rabbitmq',
            'key_perms': '440',
            'cert_perms': '444'
        }

        use_supplied_certificates(**cert_config)

    def replace_certificates(self):
        if (os.path.exists(NEW_BROKER_CERT_FILE_PATH) or
                os.path.exists(NEW_BROKER_CA_CERT_FILE_PATH)):
            logger.info(
                'Replacing certificates on the rabbitmq component')
            self._write_certs_to_config()
            self.handle_certificates()
            systemd.restart(RABBITMQ, ignore_failure=True)
            systemd.verify_alive(RABBITMQ)

    @staticmethod
    def _write_certs_to_config():
        if os.path.exists(NEW_BROKER_CERT_FILE_PATH):
            config[RABBITMQ]['cert_path'] = NEW_BROKER_CERT_FILE_PATH
            config[RABBITMQ]['key_path'] = NEW_BROKER_KEY_FILE_PATH
        if os.path.exists(NEW_BROKER_CA_CERT_FILE_PATH):
            config[RABBITMQ]['ca_path'] = NEW_BROKER_CA_CERT_FILE_PATH

    def validate_new_certs(self):
        get_and_validate_certs_for_replacement(
            default_cert_location=BROKER_CERT_LOCATION,
            default_key_location=BROKER_KEY_LOCATION,
            default_ca_location=BROKER_CA_LOCATION,
            new_cert_location=NEW_BROKER_CERT_FILE_PATH,
            new_key_location=NEW_BROKER_KEY_FILE_PATH,
            new_ca_location=NEW_BROKER_CA_CERT_FILE_PATH
        )


class Manager(BaseComponent):
    @staticmethod
    def handle_certificates():
        use_supplied_certificates(component_name=RABBITMQ,
                                  ca_destination=BROKER_CA_LOCATION)

    def replace_certificates(self):
        if (QUEUE_SERVICE not in config[SERVICES_TO_INSTALL] and
                os.path.exists(NEW_BROKER_CA_CERT_FILE_PATH)):
            logger.info('Replacing rabbitmq CA cert on the manager component')
            config[RABBITMQ]['ca_path'] = NEW_BROKER_CA_CERT_FILE_PATH
            self.handle_certificates()

    def validate_new_certs(self):
        if (QUEUE_SERVICE not in config[SERVICES_TO_INSTALL] and
                os.path.exists(NEW_BROKER_CA_CERT_FILE_PATH)):
            validate_certificates(ca_filename=NEW_BROKER_CA_CERT_FILE_PATH)


class PostgresqlClient(BaseComponent):
    def _handle_ca_certificate(self):
        use_supplied_certificates(
            ca_destination=POSTGRESQL_CA_CERT_PATH,
            component_name=POSTGRESQL_CLIENT
        )

    def _handle_cert_and_key(self):
        use_supplied_certificates(
            cert_destination=POSTGRESQL_CLIENT_CERT_PATH,
            key_destination=POSTGRESQL_CLIENT_KEY_PATH,
            key_perms='400',
            component_name=SSL_INPUTS,
            prefix='postgresql_client_'
        )

    def replace_certificates(self):
        replacing_ca = os.path.exists(NEW_POSTGRESQL_CA_CERT_FILE_PATH)
        replacing_cert_and_key = os.path.exists(
            NEW_POSTGRESQL_CLIENT_CERT_FILE_PATH)
        if config[POSTGRESQL_CLIENT][SSL_ENABLED]:
            self.validate_new_certs()
            if replacing_ca:
                logger.info(
                    'Replacing CA cert on postgresql_client component')
                config[POSTGRESQL_CLIENT]['ca_path'] = \
                    NEW_POSTGRESQL_CA_CERT_FILE_PATH
                self._handle_ca_certificate()
            if (config[POSTGRESQL_CLIENT][SSL_CLIENT_VERIFICATION] and
                    replacing_cert_and_key):
                logger.info(
                    'Replacing cert and key on postgresql_client component')
                config[SSL_INPUTS]['postgresql_client_cert_path'] = \
                    NEW_POSTGRESQL_CLIENT_CERT_FILE_PATH
                config[SSL_INPUTS]['postgresql_client_key_path'] = \
                    NEW_POSTGRESQL_CLIENT_KEY_FILE_PATH
                self._handle_cert_and_key()

    def validate_new_certs(self):
        if config[POSTGRESQL_CLIENT][SSL_ENABLED]:
            cert_filename, key_filename = None, None
            if config[POSTGRESQL_CLIENT][SSL_CLIENT_VERIFICATION]:
                cert_filename, key_filename = \
                    get_cert_and_key_filenames(
                        NEW_POSTGRESQL_CLIENT_CERT_FILE_PATH,
                        NEW_POSTGRESQL_CLIENT_KEY_FILE_PATH,
                        POSTGRESQL_CLIENT_CERT_PATH,
                        POSTGRESQL_CLIENT_KEY_PATH)

            ca_filename = get_ca_filename(NEW_POSTGRESQL_CA_CERT_FILE_PATH,
                                          POSTGRESQL_CA_CERT_PATH)

            validate_certificates(cert_filename, key_filename, ca_filename)


class RestService(BaseComponent):
    def handle_haproxy_certificate(self):
        use_supplied_certificates(
            ca_destination='/etc/haproxy/ca.crt',
            owner='haproxy',
            group='haproxy',
            component_name='postgresql_client'
        )

    @staticmethod
    def handle_ldap_certificate():
        use_supplied_certificates(
            ca_destination=LDAP_CA_CERT_PATH,
            component_name=RESTSERVICE,
            sub_component='ldap',
            just_ca_cert=True
        )

    def replace_certificates(self):
        if (DATABASE_SERVICE not in config[SERVICES_TO_INSTALL]
                and config[POSTGRESQL_SERVER]['cluster']['nodes']):
            self._replace_haproxy_cert()
        self._replace_ldap_cert()
        self._replace_ca_certs_on_db()
        systemd.restart(RESTSERVICE)
        self._verify_restservice_alive()

    def _verify_restservice(self):
        """To verify that the REST service is working, check the status

        Not everything will be green on the status, because not all
        services are set up yet, but we are just checking that the REST
        service responds.
        """
        rest_port = config[RESTSERVICE]['port']
        url = REST_URL.format(port=rest_port, endpoint='status')
        wait_for_port(rest_port)
        req = urllib2.Request(url, headers=get_auth_headers())

        try:
            response = urllib2.urlopen(req)
        # keep an erroneous HTTP response to examine its status code, but still
        # abort on fatal errors like being unable to connect at all
        except urllib2.HTTPError as e:
            response = e
        except urllib2.URLError as e:
            raise NetworkError(
                'REST service returned an invalid response: {0}'.format(e))
        if response.code != 200:
            raise NetworkError(
                'REST service returned an unexpected response: '
                '{0}'.format(response.code)
            )

        try:
            json.load(response)
        except ValueError as e:
            raise ReplaceCertificatesError(
                'REST service returned malformed JSON: {0}'.format(e))

    def _verify_restservice_alive(self):
        systemd.verify_alive(RESTSERVICE)

        logger.info('Verifying Rest service is working as expected...')
        self._verify_restservice()

    def validate_new_certs(self):
        # All other certs are validated in other components
        if os.path.exists(NEW_LDAP_CA_CERT_PATH):
            validate_certificates(ca_filename=NEW_LDAP_CA_CERT_PATH)

    def _replace_ca_certs_on_db(self):
        if os.path.exists(NEW_INTERNAL_CA_CERT_FILE_PATH):
            self._replace_manager_ca_on_db()
        if os.path.exists(NEW_BROKER_CA_CERT_FILE_PATH):
            self._replace_rabbitmq_ca_on_db()

    def _replace_manager_ca_on_db(self):
        cert_name = '{0}-ca'.format(config[MANAGER][HOSTNAME])
        self._log_replacing_certs_on_db(cert_name)
        script_input = {
            'cert_path': NEW_INTERNAL_CA_CERT_FILE_PATH,
            'name': cert_name
        }
        self._run_replace_certs_on_db_script(script_input)

    def _replace_rabbitmq_ca_on_db(self):
        self._log_replacing_certs_on_db('rabbitmq-ca')
        script_input = {
            'cert_path': NEW_BROKER_CA_CERT_FILE_PATH,
            'name': 'rabbitmq-ca'
        }
        self._run_replace_certs_on_db_script(script_input)

    def _run_replace_certs_on_db_script(self, script_input):
        configs = {
            'rest_config': REST_CONFIG_PATH,
            'authorization_config': REST_AUTHORIZATION_CONFIG_PATH,
            'security_config': REST_SECURITY_CONFIG_PATH
        }
        output = self.run_script('replace_certs_on_db.py', script_input,
                                 configs)
        logger.info(output)

    def run_script(self, script_name, script_input=None, configs=None):
        """Runs a script in a separate process.

        :param script_name: script name inside the SCRIPTS_PATH dir.
        :param script_input: script input to pass to the script.
        :param configs: keword arguments dict to pass to
        _create_process_env(..).
        :return: the script's returned when it finished its execution.
        """
        env_dict = self._create_process_env(**configs) if configs else None

        script_path = os.path.join(os.path.dirname(__file__), script_name)

        proc_result = self.run_script_on_manager_venv(script_path,
                                                      script_input,
                                                      envvars=env_dict)
        return self._get_script_stdout(proc_result)

    @staticmethod
    def _get_script_stdout(result):
        """Log stderr output from the script and return the return stdout from the
        script.
        :param result: Popen result.
        """
        if result.aggr_stderr:
            output = result.aggr_stderr.split('\n')
            output = [line.strip() for line in output if line.strip()]
            for line in output:
                logger.debug(line)
        return result.aggr_stdout if result.aggr_stdout else ""

    @staticmethod
    def run_script_on_manager_venv(script_path,
                                   script_input=None,
                                   script_input_arg='--input',
                                   envvars=None,
                                   script_args=None,
                                   json_dump=True):
        """Runs a script in a separate process inside the Cloudify Manager's venv.

        :param script_path: script absolute path.
        :param script_input: script configuration to pass to the script. The
         path will be passed with the script_conf_arg param as an argument of
         the script - unless not provided.
        :param script_input_arg: named argument to pass the script conf with.
        :param envvars: env vars to run the script with.
        :param script_args: script arguments.
        :param json_dump: if to json.dump the script_input.
        :return: process result of the run script.
        """
        if not isfile(script_path):
            raise FileError(
                'Provided script path "{0}" isn\'t a file or doesn\'t '
                'exist.'.format(script_path))
        python_path = os.path.join(REST_HOME_DIR, 'env', 'bin', 'python')
        cmd = [python_path, script_path]
        cmd.extend(script_args or [])

        if script_input:
            args_json_path = write_to_tempfile(script_input, json_dump)
            cmd.extend([script_input_arg, args_json_path])

        return sudo(cmd, env=envvars)

    @staticmethod
    def _create_process_env(rest_config=None, authorization_config=None,
                            security_config=None):
        env = {}
        for value, envvar in [
            (rest_config, 'MANAGER_REST_CONFIG_PATH'),
            (security_config, 'MANAGER_REST_SECURITY_CONFIG_PATH'),
            (authorization_config, 'MANAGER_REST_AUTHORIZATION_CONFIG_PATH'),
        ]:
            if value is not None:
                env[envvar] = value
        return env

    @staticmethod
    def _log_replacing_certs_on_db(cert_type):
        logger.info('Replacing %s in Certificate table', cert_type)

    def _replace_ldap_cert(self):
        if os.path.exists(NEW_LDAP_CA_CERT_PATH):
            validate_certificates(ca_filename=NEW_LDAP_CA_CERT_PATH)
            logger.info('Replacing ldap CA cert on the restservice component')
            config['restservice']['ldap']['ca_cert'] = NEW_LDAP_CA_CERT_PATH
            self.handle_ldap_certificate()

    def _replace_haproxy_cert(self):
        if os.path.exists(NEW_POSTGRESQL_CA_CERT_FILE_PATH):
            # The certificate was validated in the PostgresqlClient component
            logger.info(
                'Replacing haproxy cert on the restservice component')
            config[POSTGRESQL_CLIENT]['ca_path'] = \
                NEW_POSTGRESQL_CA_CERT_FILE_PATH
            self.handle_haproxy_certificate()
            systemd.restart('haproxy', append_prefix=False,
                            ignore_failure=True)
            self._wait_for_haproxy_startup()

    @staticmethod
    def get_haproxy_servers():
        # Get the haproxy status data
        try:
            haproxy_csv = requests.get(
                'http://localhost:7000/admin?stats;csv;norefresh'
            ).text
        except requests.ConnectionError as err:
            logger.info(
                'Could not connect to DB proxy ({err}), '.format(err=err)
            )
            return None

        # Example output (# noqas are not part of actual output):
        # # pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,rate_max,check_status,check_code,check_duration,hrsp_1xx,hrsp_2xx,hrsp_3xx,hrsp_4xx,hrsp_5xx,hrsp_other,hanafail,req_rate,req_rate_max,req_tot,cli_abrt,srv_abrt,comp_in,comp_out,comp_byp,comp_rsp,lastsess,last_chk,last_agt,qtime,ctime,rtime,ttime,  # noqa
        # stats,FRONTEND,,,1,1,2000,7,553,83778,0,0,0,,,,,OPEN,,,,,,,,,1,1,0,,,,0,1,0,1,,,,0,6,0,0,0,0,,1,1,7,,,0,0,0,0,,,,,,,,  # noqa
        # stats,BACKEND,0,0,0,0,200,0,553,83778,0,0,,0,0,0,0,UP,0,0,0,,0,89,0,,1,1,0,,0,,1,0,,0,,,,0,0,0,0,0,0,,,,,0,0,0,0,0,0,0,,,0,0,0,0,  # noqa
        # postgres,FRONTEND,,,0,0,2000,0,0,0,0,0,0,,,,,OPEN,,,,,,,,,1,2,0,,,,0,0,0,0,,,,,,,,,,,0,0,0,,,0,0,0,0,,,,,,,,  # noqa
        # postgres,postgresql_192.0.2.46_5432,0,0,0,0,100,0,0,0,,0,,0,0,0,0,DOWN,1,1,0,1,1,89,89,,1,2,1,,0,,2,0,,0,L7STS,503,3,,,,,,,0,,,,0,0,,,,,-1,HTTP status check returned code <503>,,0,0,0,0,  # noqa
        # postgres,postgresql_192.0.2.47_5432,0,0,0,0,100,0,0,0,,0,,0,0,0,0,UP,1,1,0,0,0,89,0,,1,2,2,,0,,2,0,,0,L7OK,200,3,,,,,,,0,,,,0,0,,,,,-1,HTTP status check returned code <200>,,0,0,0,0,  # noqa
        # postgres,postgresql_192.0.2.48_5432,0,0,0,0,100,0,0,0,,0,,0,0,0,0,DOWN,1,1,0,1,1,87,87,,1,2,3,,0,,2,0,,0,L7STS,503,2,,,,,,,0,,,,0,0,,,,,-1,HTTP status check returned code <503>,,0,0,0,0,  # noqa
        # postgres,BACKEND,0,0,0,0,200,0,0,0,0,0,,0,0,0,0,UP,1,1,0,,0,89,0,,1,2,0,,0,,1,0,,0,,,,,,,,,,,,,,0,0,0,0,0,0,-1,,,0,0,0,0,  # noqa
        haproxy_status = list(csv.DictReader(
            haproxy_csv.lstrip('# ').splitlines()
        ))

        servers = [
            row for row in haproxy_status
            if row['svname'] not in ('BACKEND', 'FRONTEND')
        ]

        for server in servers:
            logger.debug(
                'Server: {name}: {status} ({why}) - {detail}'.format(
                    name=server['svname'],
                    status=server['status'],
                    why=server['check_status'],
                    detail=server['last_chk'],
                )
            )

        return servers

    def _wait_for_haproxy_startup(self):
        logger.info('Waiting for DB proxy startup to complete...')
        healthy = False
        for attempt in range(60):
            servers = self.get_haproxy_servers()

            if not servers:
                # No results yet
                logger.info('Haproxy not responding, retrying...')
                time.sleep(1)
                continue

            if any(server['check_status'] == 'INI' for server in servers):
                logger.info('DB healthchecks still initialising...')
                time.sleep(1)
                continue

            if not any(server['status'] == 'UP' for server in servers):
                logger.info('DB proxy has not yet selected a backend DB...')
                time.sleep(1)
                continue

            healthy = True
            # If we got here, haproxy is happy!
            break

        if not healthy:
            raise RuntimeError(
                'DB proxy startup failed.'
            )

        logger.info('DB proxy startup complete.')


class Nginx(BaseComponent):
    def _handle_internal_cert(self, replacing_ca=False):
        """
        The user might provide the internal cert and the internal key, or
        neither. It is an error to only provide one of them. If the user did
        not provide the internal cert+key, we must generate it, but we can only
        generate it if we have a CA key (either provided or generated).
        So it is an error to provide only the CA cert, and then not provide
        the internal cert+key.
        """
        cert_destinations = {
            'cert_destination': INTERNAL_CERT_PATH,
            'key_destination': INTERNAL_KEY_PATH,
        }
        if replacing_ca:
            cert_destinations['ca_destination'] = CA_CERT_PATH
        logger.info('Handling internal certificate...')
        use_supplied_certificates(
            SSL_INPUTS,
            prefix='internal_',
            validate_certs_src_exist=True,
            **cert_destinations
        )

    def replace_certificates(self):
        if self._needs_to_replace_internal_certs():
            self._replace_internal_certs()
        if self._needs_to_replace_external_certs():
            self._replace_external_certs()

        if (self._needs_to_replace_internal_certs() or
                self._needs_to_replace_external_certs()):
            systemd.restart(NGINX, append_prefix=False)
            systemd.verify_alive(NGINX, append_prefix=False)

    @staticmethod
    def _needs_to_replace_internal_certs():
        return (os.path.exists(NEW_INTERNAL_CERT_FILE_PATH) or
                os.path.exists(NEW_INTERNAL_CA_CERT_FILE_PATH))

    @staticmethod
    def _needs_to_replace_external_certs():
        return (os.path.exists(NEW_EXTERNAL_CERT_FILE_PATH) or
                os.path.exists(NEW_EXTERNAL_CA_CERT_FILE_PATH))

    def validate_new_certs(self):
        self._validate_internal_certs()
        self._validate_external_certs()

    def _validate_internal_certs(self):
        if self._needs_to_replace_internal_certs():
            get_and_validate_certs_for_replacement(
                default_cert_location=INTERNAL_CERT_PATH,
                default_key_location=INTERNAL_KEY_PATH,
                default_ca_location=CA_CERT_PATH,
                new_cert_location=NEW_INTERNAL_CERT_FILE_PATH,
                new_key_location=NEW_INTERNAL_KEY_FILE_PATH,
                new_ca_location=NEW_INTERNAL_CA_CERT_FILE_PATH
            )

    def _validate_external_certs(self):
        if self._needs_to_replace_external_certs():
            get_and_validate_certs_for_replacement(
                default_cert_location=EXTERNAL_CERT_PATH,
                default_key_location=EXTERNAL_KEY_PATH,
                default_ca_location=CA_CERT_PATH,
                new_cert_location=NEW_EXTERNAL_CERT_FILE_PATH,
                new_key_location=NEW_EXTERNAL_KEY_FILE_PATH,
                new_ca_location=NEW_EXTERNAL_CA_CERT_FILE_PATH
            )

    def _replace_internal_certs(self):
        self._validate_internal_certs()
        self.log_replacing_certificates('internal certificates')
        self._write_internal_certs_to_config()
        replacing_ca = os.path.exists(NEW_INTERNAL_CA_CERT_FILE_PATH)
        self._handle_internal_cert(replacing_ca=replacing_ca)

    def _replace_external_certs(self):
        self._validate_external_certs()
        self.log_replacing_certificates('external certificates')
        self._write_external_certs_to_config()
        replacing_ca = os.path.exists(NEW_EXTERNAL_CA_CERT_FILE_PATH)
        self._handle_external_cert(replacing_ca=replacing_ca)

    @staticmethod
    def log_replacing_certificates(certs_type):
        logger.info('Replacing %s on nginx component', certs_type)

    @staticmethod
    def _write_internal_certs_to_config():
        if os.path.exists(NEW_INTERNAL_CERT_FILE_PATH):
            config[SSL_INPUTS]['internal_cert_path'] = \
                NEW_INTERNAL_CERT_FILE_PATH
            config[SSL_INPUTS]['internal_key_path'] = \
                NEW_INTERNAL_KEY_FILE_PATH
        if os.path.exists(NEW_INTERNAL_CA_CERT_FILE_PATH):
            config[SSL_INPUTS]['ca_cert_path'] = \
                NEW_INTERNAL_CA_CERT_FILE_PATH

    @staticmethod
    def _write_external_certs_to_config():
        if os.path.exists(NEW_EXTERNAL_CERT_FILE_PATH):
            config[SSL_INPUTS]['external_cert_path'] = \
                NEW_EXTERNAL_CERT_FILE_PATH
            config[SSL_INPUTS]['external_key_path'] = \
                NEW_EXTERNAL_KEY_FILE_PATH
        if os.path.exists(NEW_EXTERNAL_CA_CERT_FILE_PATH):
            config[SSL_INPUTS]['external_ca_cert_path'] = \
                NEW_EXTERNAL_CA_CERT_FILE_PATH

    @staticmethod
    def _handle_external_cert(replacing_ca=False):
        cert_destinations = {
            'cert_destination': EXTERNAL_CERT_PATH,
            'key_destination': EXTERNAL_KEY_PATH,
        }
        if replacing_ca:
            cert_destinations['ca_destination'] = EXTERNAL_CA_CERT_PATH
        logger.info('Handling external certificate...')
        use_supplied_certificates(
            SSL_INPUTS,
            prefix='external_',
            **cert_destinations
        )


class Stage(BaseComponent):
    @staticmethod
    def _handle_ca_certificate():
        use_supplied_certificates(
            component_name=POSTGRESQL_CLIENT,
            ca_destination=STAGE_DB_CA_PATH,
            owner=STAGE_USER,
            group=STAGE_GROUP,
        )

    @staticmethod
    def _handle_cert_and_key():
        use_supplied_certificates(
            component_name=SSL_INPUTS,
            prefix='postgresql_client_',
            cert_destination=STAGE_DB_CLIENT_CERT_PATH,
            key_destination=STAGE_DB_CLIENT_KEY_PATH,
            owner=STAGE_USER,
            group=STAGE_GROUP,
            key_perms='400',
        )

    def replace_certificates(self):
        # The certificates are validated in the PostgresqlClient component
        replacing_ca = os.path.exists(NEW_POSTGRESQL_CA_CERT_FILE_PATH)
        replacing_cert_and_key = os.path.exists(
            NEW_POSTGRESQL_CLIENT_CERT_FILE_PATH)

        if config[POSTGRESQL_CLIENT][SSL_ENABLED]:
            if replacing_ca:
                self.log_replacing_certs('CA cert')
                self._handle_ca_certificate()

            if (config[POSTGRESQL_CLIENT][SSL_CLIENT_VERIFICATION] and
                    replacing_cert_and_key):
                self.log_replacing_certs('cert and key')
                self._handle_cert_and_key()

            systemd.restart(STAGE)
            self._verify_stage_alive()

    @staticmethod
    def _verify_stage_alive():
        systemd.verify_alive(STAGE)
        wait_for_port(8088)

    def log_replacing_certs(self, certs_type):
        logger.info(
            'Replacing {0} on stage component'.format(certs_type))


class Composer(BaseComponent):
    @staticmethod
    def _handle_ca_certificate():
        use_supplied_certificates(
            component_name=POSTGRESQL_CLIENT,
            ca_destination=COMPOSER_DB_CA_PATH,
            owner=COMPOSER_USER,
            group=COMPOSER_GROUP,
        )

    @staticmethod
    def _handle_cert_and_key():
        use_supplied_certificates(
            component_name=SSL_INPUTS,
            prefix='postgresql_client_',
            cert_destination=COMPOSER_DB_CLIENT_CERT_PATH,
            key_destination=COMPOSER_DB_CLIENT_KEY_PATH,
            owner=COMPOSER_USER,
            group=COMPOSER_GROUP,
            key_perms='400',
        )

    def replace_certificates(self):
        # The certificates are validated in the PostgresqlClient component
        replacing_ca = os.path.exists(NEW_POSTGRESQL_CA_CERT_FILE_PATH)
        replacing_cert_and_key = os.path.exists(
            NEW_POSTGRESQL_CLIENT_CERT_FILE_PATH)

        if config[POSTGRESQL_CLIENT][SSL_ENABLED]:
            if replacing_ca:
                self.log_replacing_certs('CA cert')
                self._handle_ca_certificate()
            if (config[POSTGRESQL_CLIENT][SSL_CLIENT_VERIFICATION] and
                    replacing_cert_and_key):
                self.log_replacing_certs('cert and key')
                self._handle_cert_and_key()

            systemd.restart(COMPOSER)
            self._verify_composer_alive()

    @staticmethod
    def _verify_composer_alive():
        systemd.verify_alive(COMPOSER)
        wait_for_port(COMPOSER_PORT)

    @staticmethod
    def log_replacing_certs(certs_type):
        logger.info('Replacing %s on composer component', certs_type)


def get_components():
    _components = []

    if DATABASE_SERVICE in config[SERVICES_TO_INSTALL]:
        _components += [PostgresqlServer()]

    if QUEUE_SERVICE in config[SERVICES_TO_INSTALL]:
        _components += [RabbitMQ()]

    if MANAGER_SERVICE in config[SERVICES_TO_INSTALL]:
        _components += [
            Manager(),
            PostgresqlClient(),
            RestService(),
            Nginx(),
            Stage(),
            Composer()
        ]

    return _components


def _replace_certificates():
    logger.info('Replacing certificates')
    for component in get_components():
        try:
            component.replace_certificates()
        except Exception as err:  # There isn't a specific exception
            raise ReplaceCertificatesError(
                'An error occurred while replacing certificates: '
                '{0}'.format(err))

    logger.info('Configuring status-reporter')

    if MANAGER_SERVICE in config[SERVICES_TO_INSTALL]:
        systemd.restart('mgmtworker')
        systemd.restart('amqp-postgres')
        if os.path.exists(NEW_INTERNAL_CA_CERT_FILE_PATH):
            run('cfy_manager status-reporter configure --ca-path '
                '{0}'.format(CA_CERT_PATH))

    if DATABASE_SERVICE in config[SERVICES_TO_INSTALL]:
        if os.path.exists(NEW_POSTGRESQL_CA_CERT_FILE_PATH):
            run('cfy_manager status-reporter configure --ca-path '
                '{0}'.format(ETCD_CA_PATH))

    if QUEUE_SERVICE in config[SERVICES_TO_INSTALL]:
        if os.path.exists(NEW_BROKER_CA_CERT_FILE_PATH):
            run('cfy_manager status-reporter configure --ca-path '
                '{0}'.format(BROKER_CA_LOCATION))


def _only_validate():
    logger.info('Validating new certificates')
    for component in get_components():
        try:
            component.validate_new_certs()
        except (ValueError, ValidationError, ProcessExecutionError) as err:
            raise ReplaceCertificatesError(
                'An error occurred while validating certificates: '
                '{0}'.format(err))


def replace_certificates():
    """ Replacing the certificates on the current instance """
    parser = argparse.ArgumentParser(description='Replacing certificates on '
                                                 'instance')
    parser.add_argument('--only-validate', action='store_true', default=False,
                        help='Validate the provided certificates. '
                             'If this flag is on, then the certificates will '
                             'only be validated and not replaced.')
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        dest='verbose')
    args = parser.parse_args()
    if args.verbose:
        stdout_handler = logger.handlers[0]
        stdout_handler.setLevel(logging.DEBUG)

    config.load_config()
    if args.only_validate:
        _only_validate()
    else:
        _replace_certificates()


if __name__ == '__main__':
    replace_certificates()
