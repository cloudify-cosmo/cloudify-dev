import os
import sys
import shlex
import socket
import logging
import argparse
import subprocess
from io import StringIO
from os.path import join
from tempfile import mkstemp

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

INITIAL_INSTALL_DIR = '/etc/cloudify/.installed'
INSTALLED_COMPONENTS_FILE = join(INITIAL_INSTALL_DIR, 'components.yaml')
INSTALLED_PACKAGES = join(INITIAL_INSTALL_DIR, 'packages.yaml')

logger = logging.getLogger(socket.gethostname())

SOURCES = {
    'manager': ['cloudify-management-worker', 'cloudify-rest-service',
                'cloudify-cli', 'cloudify-manager-ip-setter', 'nginx',
                'python-psycopg2', 'postgresql95', 'cloudify-agents',
                'patch', 'nodejs', 'cloudify-stage'],
    'manager_premium': ['cloudify-premium', 'cloudify-composer'],
    'manager_cluster': ['haproxy'],
    'db': ['postgresql95', 'postgresql95-server', 'postgresql95-contrib',
           'libxslt'],
    'db_cluster': ['libestr', 'libfastjson', 'rsyslog', 'etcd', 'patroni'],
    'queue': ['rabbitmq-server-3.8.4', 'cloudify-rabbitmq'],
    'queue_cluster': [],
    'prometheus': ['prometheus', 'node_exporter', 'blackbox_exporter',
                   'postgres_exporter'],
    'prometheus_cluster': ['nginx'],
    'haveged': ['haveged']
}


class ProcessExecutionError(BaseException):
    def __init__(self, message, return_code=None):
        self.return_code = return_code
        super(ProcessExecutionError, self).__init__(message)


def setup_logger(verbose):
    msg_format = '%(name)s - %(levelname)s - %(message)s'
    logger.setLevel(logging.DEBUG)
    out_sh = logging.StreamHandler(sys.stdout)
    out_sh.setLevel(logging.DEBUG if verbose else logging.INFO)
    out_sh.setFormatter(logging.Formatter(msg_format))
    logger.addHandler(out_sh)


def run(command, stdout=None, ignore_failures=False):
    if isinstance(command, str):
        command = shlex.split(command)

    stdout = stdout or subprocess.PIPE
    logger.debug('Running: {0}'.format(command))
    proc = subprocess.Popen(command, stdin=subprocess.PIPE,
                            stdout=stdout, stderr=subprocess.PIPE)
    proc.aggr_stdout, proc.aggr_stderr = proc.communicate(input=u'')
    if proc.aggr_stdout is not None:
        proc.aggr_stdout = proc.aggr_stdout.decode('utf-8')
    if proc.aggr_stderr is not None:
        proc.aggr_stderr = proc.aggr_stderr.decode('utf-8')
    if proc.returncode != 0:
        if not ignore_failures:
            msg = 'Failed running command: {0} ({1}).'.format(
                command, proc.aggr_stderr)
            err = ProcessExecutionError(msg, proc.returncode)
            err.aggr_stdout = proc.aggr_stdout
            err.aggr_stderr = proc.aggr_stderr
            raise err
    return proc


def sudo(command, *args, **kwargs):
    if isinstance(command, str):
        command = shlex.split(command)
    command.insert(0, 'sudo')
    return run(command=command, *args, **kwargs)


def is_file(file_path):
    """Is the path a file?"""
    return sudo(['test', '-f', file_path], ignore_failures=True
                ).returncode == 0


def sudo_read(path):
    return sudo(['cat', path]).aggr_stdout


def write_to_tempfile(contents):
    fd, file_path = mkstemp()
    os.close(fd)

    with open(file_path, 'w') as f:
        f.write(contents)

    return file_path


def ensure_destination_dir_exists(destination):
    destination_dir = os.path.dirname(destination)
    if not os.path.exists(destination_dir):
        logger.debug(
            'Path does not exist: {0}. Creating it...'.format(
                destination_dir))
        sudo(['mkdir', '-p', destination_dir])


def move(source, destination):
    ensure_destination_dir_exists(destination)
    sudo(['cp', source, destination])
    sudo(['rm', source])


def write_to_file(contents, destination):
    """ Used to write files to locations that require sudo to access """
    temp_path = write_to_tempfile(contents)
    move(temp_path, destination)


def touch(file_path):
    """ Create an empty file in the provided path """
    ensure_destination_dir_exists(file_path)
    sudo(['touch', file_path])


def read_yaml_file(yaml_path):
    """Loads a YAML file.

    :param yaml_path: the path to the yaml file.
    :return: YAML file parsed content.
    """
    if is_file(yaml_path):
        try:
            file_content = sudo_read(yaml_path)
            yaml = YAML(typ='safe', pure=True)
            return yaml.load(file_content)
        except YAMLError as e:
            raise YAMLError('Failed to load yaml file {0}, due to {1}'
                            ''.format(yaml_path, str(e)))
    return None


def update_yaml_file(yaml_path, updated_content):
    if not isinstance(updated_content, dict):
        raise ValueError('Expected input of type dict, got {0} '
                         'instead'.format(type(updated_content)))

    yaml_content = read_yaml_file(yaml_path) or {}
    yaml_content.update(**updated_content)
    stream = StringIO()
    yaml = YAML(typ='safe')
    yaml.default_flow_style = False
    yaml.dump(yaml_content, stream)
    write_to_file(stream.getvalue(), yaml_path)


def _is_premium_installed():
    installed = run(['rpm', '-q', 'cloudify-premium'], ignore_failures=True)
    return installed.returncode == 0


def _is_installed(config, service):
    return service in config['services_to_install']


def _get_components(config):
    _components = []

    if _is_installed(config, 'database_service'):
        _components.append('postgresqlserver')

    if _is_installed(config, 'queue_service'):
        _components.append('rabbitmq')

    if _is_installed(config, 'manager_service'):
        _components += [
            'manager',
            'postgresqlclient',
            'restservice',
            'manageripsetter',
            'nginx',
            'cli',
            'amqppostgres',
            'mgmtworker',
            'stage',
        ]

        if (_is_premium_installed()
                and not config.get('composer', {}).get('skip_installation')):
            _components.append('composer')

        _components.append('usagecollector')

        if not config.get('sanity', {}).get('skip_sanity'):
            _components.append('sanity')

    if _is_installed(config, 'monitoring_service'):
        _components.append('prometheus')
        if not _is_installed(config, 'manager_service'):
            _components.append('nginx')

    if _is_installed(config, 'entropy_service'):
        _components.append('haveged')

    return _components


def _get_packages(config):
    """Yum packages to install/uninstall, based on the current config"""
    packages = []
    # Adding premium components on all, even if we're on community, because
    # yum will return 0 (success) if any packages install successfully even if
    # some of the specified packages don't exist.
    if _is_installed(config, 'manager_service'):
        packages += SOURCES['manager']
        # Premium components
        packages += SOURCES['manager_cluster'] + SOURCES['manager_premium']

    if _is_installed(config, 'database_service'):
        packages += SOURCES['db']
        # Premium components
        packages += SOURCES['db_cluster']

    if _is_installed(config, 'queue_service'):
        packages += SOURCES['queue']
        # Premium components
        packages += SOURCES['queue_cluster']

    if _is_installed(config, 'monitoring_service'):
        packages += SOURCES['prometheus']
        # Premium components
        packages += SOURCES['prometheus_cluster']

    if _is_installed(config, 'entropy_service'):
        packages += SOURCES['haveged']

    return packages


def create_installation_files(config_path):
    logger.info('Creating necessary files for Cloudify removal')
    config = read_yaml_file(config_path)
    for service_name in config['services_to_install']:
        touch(join(INITIAL_INSTALL_DIR, service_name))
        if (service_name in
                ['database_service', 'queue_service', 'manager_service']):
            update_yaml_file(INSTALLED_COMPONENTS_FILE,
                             {service_name: _get_components(config)})
            update_yaml_file(INSTALLED_PACKAGES,
                             {service_name: _get_packages(config)})


def remove_cloudify(config_path, verbose):
    logger.info('Removing Cloudify')
    cmd = ['cfy_manager', 'remove', '-c', config_path]
    if verbose:
        cmd.insert(2, '-v')
    run(cmd, stdout=sys.stdout)


def main():
    """Removing a failed Cloudify v5.1 installation.

    v5.1 has a bug that causes `cfy_manager remove` to throw an error
    in case of a failed installation. This script fixes this behavior and
    removes Cloudify.
    """
    parser = argparse.ArgumentParser(
        description='Removing a failed Cloudify v5.1 installation')
    parser.add_argument('-c',
                        dest='config_path',
                        help='config.yaml path',
                        default='/etc/cloudify/config.yaml')
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        default=False, help='Show verbose output')

    args = parser.parse_args()
    setup_logger(args.verbose)
    create_installation_files(args.config_path)
    remove_cloudify(args.config_path, args.verbose)


if __name__ == '__main__':
    main()
