import sys
import logging
from os.path import dirname

from fabric import Connection
from paramiko import AuthenticationException


NEW_CERTS_TMP_DIR_PATH = '/tmp/new_cloudify_certs/'
REMOTE_SCRIPT_PATH = NEW_CERTS_TMP_DIR_PATH + 'replace_certificates.py'
REMOTE_REQUIREMENTS_PATH = NEW_CERTS_TMP_DIR_PATH + 'instance_requirements.txt'


class ReplaceCertificatesError(Exception):
    pass


def init_logger():
    log = logging.getLogger('MAIN')
    log.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)
    return log


logger = init_logger()


class Node(object):
    def __init__(self,
                 host_ip,
                 username,
                 key_file_path,
                 node_type,
                 node_dict,
                 verbose):
        self.host_ip = host_ip
        self.node_type = node_type
        self.username = username
        self.key_file_path = key_file_path
        self.connection = self._create_connection()
        self.node_dict = node_dict
        self.verbose = verbose
        self.prepare_env()

    def _create_connection(self):
        try:
            return Connection(
                host=self.host_ip, user=self.username, port=22,
                connect_kwargs={'key_filename': self.key_file_path})

        except AuthenticationException as e:
            raise ReplaceCertificatesError(
                "SSH: could not connect to {host} "
                "(username: {user}, key: {key}): {exc}".format(
                    host=self.host_ip, user=self.username,
                    key=self.key_file_path, exc=e))

    def prepare_env(self):
        commands_list = [
            'sudo yum install -y epel-release',
            'sudo yum install -y python-pip',
        ]
        hide = 'stderr' if self.verbose else 'both'
        logger.info('Preparing env for host %s', self.host_ip)
        self._prepare_new_certs_dir()
        self.put_file('{0}/instance_requirements.txt'.format(
            dirname(__file__)), REMOTE_REQUIREMENTS_PATH)
        self.put_file('{0}/replace_certificates.py'.format(dirname(__file__)),
                      REMOTE_SCRIPT_PATH)
        self.put_file('{0}/replace_certs_on_db.py'.format(dirname(__file__)),
                      NEW_CERTS_TMP_DIR_PATH+'replace_certs_on_db.py')
        for command in commands_list:
            self.run_command(command, hide=hide)
        self.run_command('sudo pip install -q -r '
                         '{0}'.format(REMOTE_REQUIREMENTS_PATH), hide=hide)

    def run_command(self, command, hide='stderr'):
        logger.debug('Running `%s` on %s', command, self.host_ip)
        result = self.connection.run(command, warn=True, hide=hide)
        if result.failed:
            raise ReplaceCertificatesError(
                'The command `{0}` on host {1} failed with the error: '
                '{2}'.format(command, self.host_ip, str(result.stderr)))
        return result

    def put_file(self, local_path, remote_path):
        logger.debug('Copying %s to %s on host %s',
                     local_path, remote_path, self.host_ip)
        self.connection.put(local_path, remote_path)

    def replace_certificates(self):
        logger.info('Replacing certificates on host %s', self.host_ip)
        self._pass_certificates()
        command = 'sudo python {0}'.format(REMOTE_SCRIPT_PATH)
        if self.verbose:
            command += ' --verbose'
        self.run_command(command)
        logger.info('Done. Deleting the replace-certificates temp dir '
                    'on host %s.', self.host_ip)
        self.run_command('rm -rf {0}'.format(NEW_CERTS_TMP_DIR_PATH))

    def validate_certificates(self):
        logger.info('Validating certificates for host %s', self.host_ip)
        command = 'sudo python {0} --only-validate'.format(REMOTE_SCRIPT_PATH)
        if self.verbose:
            command += ' --verbose'
        self.run_command(command)

    def _pass_certificates(self):
        for cert_name, new_cert_path in self.node_dict.items():
            self.put_file(new_cert_path, self._get_remote_cert_path(cert_name))

    def _get_remote_cert_path(self, cert_name):
        new_cert_path = (('new_' + self.node_type + '_' + cert_name[4:])
                         if self.node_type in ('postgresql_server', 'rabbitmq')
                         else cert_name)
        return NEW_CERTS_TMP_DIR_PATH + new_cert_path + '.pem'

    def _prepare_new_certs_dir(self):
        logger.info('Creating the replace-certificates temp-dir on '
                    'host %s', self.host_ip)
        self.run_command('sudo rm -rf {0}; mkdir {0}'.format(
            NEW_CERTS_TMP_DIR_PATH))


class ReplaceCertificatesConfig(object):
    def __init__(self, config_dict, verbose):
        self.config_dict = config_dict
        self.username = config_dict.get('username')
        self.key_file_path = config_dict.get('key_file_path')
        self.relevant_nodes_dict = {'manager': [],
                                    'postgresql_server': [],
                                    'rabbitmq': []}
        self._create_nodes(verbose)
        self.needs_to_replace_certificates = len(self.relevant_nodes) > 0

    @property
    def relevant_nodes(self):
        relevant_nodes = []
        for instance_name in 'postgresql_server', 'rabbitmq', 'manager':
            relevant_nodes.extend(self.relevant_nodes_dict[instance_name])
        return relevant_nodes

    def validate_certificates(self):
        logger.info('Validating certificates')
        for node in self.relevant_nodes:
            try:
                node.validate_certificates()
            except ReplaceCertificatesError as err:
                self._close_clients_connection()
                raise err

    def replace_certificates(self):
        logger.info('Replacing certificates')
        for node in self.relevant_nodes:
            try:
                node.replace_certificates()
            except ReplaceCertificatesError as err:
                self._close_clients_connection()
                raise err
        self._validate_cluster_is_healthy()
        self._close_clients_connection()

    def _validate_cluster_is_healthy(self):
        managers = self.relevant_nodes_dict['manager']
        if managers:
            manager = managers[0]  # Adding try-except block
            try:
                cluster_status_str = manager.run_command(
                    'cfy cluster status --json', hide='both').stdout
            except ReplaceCertificatesError:
                logger.info(
                    'Please change your CLI CA cert in case you are '
                    'using this code from a client. You can do this by using '
                    '`cfy profiles set -c <new-ca-cert-path>`')
                logger.info('Afterwards, run `cfy cluster status`'
                            ' and verify it is OK')
                return

            if cluster_status_str[12:14] == 'OK':
                logger.info('Successfully replaced certificates')
                logger.info(
                    'You might need to change your CLI CA cert in case you '
                    'are using this code from a client. You can do this by '
                    'using `cfy profiles set -c <new-ca-cert-path>`')
                return
            else:
                raise ReplaceCertificatesError(
                    'Failed replacing certificates. '
                    'cluster status: {0}'.format(str(cluster_status_str)))
        else:
            logger.info('Please run `cfy cluster status` on one of the '
                        'managers and verify it is OK')

    def _create_nodes(self, verbose):
        for instance_type, instance_dict in self.config_dict.items():
            if instance_type in ['username', 'key_file_path']:
                continue
            for node in instance_dict['cluster_members']:
                node_dict = self._create_node_dict(node, instance_type)
                if node_dict:
                    new_node = Node(
                        node.get('host_ip'),
                        self.username,
                        self.key_file_path,
                        instance_type,
                        node_dict,
                        verbose)
                    self.relevant_nodes_dict[instance_type].append(new_node)

    def _create_node_dict(self, node, instance_type):
        node_dict = {}
        for cert_name, cert_path in node.items():
            if (cert_name == 'host_ip') or (not cert_path):
                continue
            node_dict[cert_name] = cert_path

        for ca_cert, ca_path in self.config_dict[instance_type].items():
            if (ca_cert == 'cluster_members') or (not ca_path):
                continue
            node_dict[ca_cert] = ca_path

        if instance_type == 'manager':
            postgresql_ca_cert = self.config_dict['postgresql_server'].get(
                'new_ca_cert')
            if postgresql_ca_cert:
                node_dict['new_postgresql_server_ca_cert'] = postgresql_ca_cert

            rabbitmq_ca_cert = self.config_dict['rabbitmq'].get('new_ca_cert')
            if rabbitmq_ca_cert:
                node_dict['new_rabbitmq_ca_cert'] = rabbitmq_ca_cert

        return node_dict

    def _close_clients_connection(self):
        for node in self.relevant_nodes:
            node.connection.close()