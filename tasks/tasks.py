########
# Copyright (c) 2013 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

# flake8: noqa

import json
import os
import sys
from contextlib import contextmanager
from StringIO import StringIO
from fabric.api import *
from fabric.contrib import files

MANAGER_BRANCH = 'master'

# root of synced folder with cloudify github repositories
CODE_BASE = '/home/vagrant/cloudify'

# path to different cloudify components relative to 'CODE_BASE'
CLOUDIFY_MANAGER = 'cloudify-manager'
PACKAGER = 'cloudify-packager'

# agent package creation paths
AGENT_VIRTUALENV_PACKAGE = '/home/vagrant/package'
AGENT_VIRTUALENV_PARENT = '{0}/linux'.format(AGENT_VIRTUALENV_PACKAGE)
AGENT_VIRTUALENV_PATH = '{0}/env'.format(AGENT_VIRTUALENV_PARENT)

VIRTUALENV_PATH_MANAGER = '/opt/manager/'
VIRTUALENV_PATH_CELERY_MANAGER = '/opt/celery/cloudify.management__worker/env'
MANAGER_PACKAGES_INSTALLED_INDICATOR = '/home/vagrant/manager_packages_installed'


# packages that need to be installed under the rest service
# virtualenv, relative to the CODE_BASE
MANAGER_REST_PACKAGES = [
    ('cloudify-dsl-parser', 'cloudify-dsl-parser'),
    ('cloudify-manager/rest-service', 'cloudify-rest-service'),
    ('cloudify-amqp-influxdb', 'cloudify-amqp-influxdb')
]

# packages that need to be installed under the management worker
# virtualenv, relative to the CODE_BASE
MANAGEMENT_WORKER_PACKAGES = [
    ('cloudify-common', 'cloudify-common'),
    ('cloudify-manager/plugins/agent-installer', 'cloudify-agent-installer-plugin'),
    ('cloudify-manager/plugins/plugin-installer', 'cloudify-plugin-installer-plugin'),
    ('cloudify-manager/plugins/riemann-controller', 'cloudify-riemann-controller-plugin'),
    ('cloudify-manager/workflows', 'cloudify-workflows')
]


# packages to install (in this order) for the agent package virtualenv
AGENT_PACKAGES = [
    ('cloudify-common', 'cloudify-common'),
    ('cloudify-manager/plugins/agent-installer', 'cloudify-agent-installer-plugin'),
    ('cloudify-manager/plugins/plugin-installer', 'cloudify-plugin-installer-plugin'),
    ('cloudify-manager/plugins/windows-agent-installer', 'cloudify-windows-agent-installer-plugin'),
    ('cloudify-manager/plugins/windows-plugin-installer', 'cloudify-windows-plugin-installer-plugin')
]


AGENT_DEPENDENCIES = [
    'celery==3.0.24',
    'pyzmq==14.3.1'
]


MANAGER_RESOURCES_LINKS = {
    '/opt/manager/resources/': {
        'packages/scripts': '{0}/package-configuration/ubuntu-agent'.format(PACKAGER),
        'packages/templates': '{0}/package-configuration/ubuntu-agent'.format(PACKAGER),
        'cloudify': '{0}/resources/rest-service/cloudify'.format(CLOUDIFY_MANAGER)
    }
}

# services to stop (and start in reverse order) when starting (and ending)
# setup_env task
MANAGED_SERVICES = [
    'manager',
    'celeryd-cloudify-management',
    'amqpflux',
    'riemann',
]


def setup_dev_env():
    _validate_sources_path()
    link_manager_sources()
    link_manager_resources()
    update_agent_package()
    restart_services()


def link_manager_sources():
    if not files.exists(MANAGER_PACKAGES_INSTALLED_INDICATOR):
        with virtualenv(VIRTUALENV_PATH_MANAGER):
            for package_tuple in MANAGER_REST_PACKAGES:
                package_path = package_tuple[0]
                package_name = package_tuple[1]
                _pip_uninstall(package_name, use_sudo=True)
                _pip_install('-e {0}/{1}'.format(CODE_BASE, package_path),
                             use_sudo=True)
        with virtualenv(VIRTUALENV_PATH_CELERY_MANAGER):
            for package_tuple in MANAGEMENT_WORKER_PACKAGES:
                package_path = package_tuple[0]
                package_name = package_tuple[1]
                _pip_uninstall(package_name, use_sudo=True)
                _pip_install('-e {0}/{1}'.format(CODE_BASE, package_path),
                             use_sudo=True)
        run('touch {}'.format(MANAGER_PACKAGES_INSTALLED_INDICATOR))


def link_manager_resources():
    _link(MANAGER_RESOURCES_LINKS)


def update_agent_package():
    if files.exists(AGENT_VIRTUALENV_PARENT):
        run('rm -rf {0}'.format(AGENT_VIRTUALENV_PARENT))
    run('mkdir -p {0}'.format(AGENT_VIRTUALENV_PARENT))
    run('virtualenv {0}'.format(AGENT_VIRTUALENV_PATH))
    with virtualenv(AGENT_VIRTUALENV_PATH):
        for dependency in AGENT_DEPENDENCIES:
            _pip_install(dependency)
        for package_tuple in AGENT_PACKAGES:
            package_path = package_tuple[0]
            _pip_install('{0}/{1}'.format(CODE_BASE, package_path))
    run('tar czf package.tar.gz package')
    agent_package_path = '/opt/manager/resources/packages/agents/Ubuntu-{0}-agent.tar.gz' \
        .format(get_distribution_codename())
    sudo('cp package.tar.gz {0}'.format(agent_package_path))
    run('rm package.tar.gz')


def restart_services():
    stop_services()
    start_services()


def stop_services():
    for service in MANAGED_SERVICES:
        sudo('stop {}'.format(service))


def start_services():
    for service in MANAGED_SERVICES[::-1]:
        sudo('start {}'.format(service))


def _link(links):
    for base, sublinks in links.items():
        for sublink, target in sublinks.items():
            source = '{0}/{1}'.format(base, sublink)
            target = '{0}/{1}'.format(CODE_BASE, target)
            if files.is_link(source):
                continue
            run(' && '.join([
                'sudo rm -rf {0}'.format(source),
                'cd $(dirname {0})'.format(source),
                'sudo ln -s {0} $(basename {1})'.format(target, source)
                ]))


def _pip_install(python_package, use_sudo=False):
    if use_sudo:
        run('sudo pip install {0}'.format(python_package))
    else:
        run('pip install {0}'.format(python_package))


def _pip_uninstall(python_package, use_sudo=False):
    if use_sudo:
        run('sudo pip uninstall -y {0}'.format(python_package))
    else:
        run('pip uninstall -y {0}'.format(python_package))


def _validate_sources_path():
    stdout = StringIO()
    run('ls -l {0}'.format(CODE_BASE), stdout=stdout)
    cloudify_projects = stdout.getvalue()
    all_packages = []
    all_packages.extend(get_packages_paths(AGENT_PACKAGES))
    all_packages.extend(get_packages_paths(MANAGER_REST_PACKAGES))
    all_packages.extend(get_packages_paths(MANAGEMENT_WORKER_PACKAGES))
    missing_projects = []
    for package_name in all_packages:
        if '/' in package_name:
            directory = package_name[:package_name.find('/')]
        else:
            directory = package_name
        if directory not in cloudify_projects:
            missing_projects.append(directory)
    if missing_projects:
        print 'Cannot link source. Missing projects detected on host machine: {0}'\
            .format(os.linesep.join(missing_projects))
        print 'Make sure you have all the necessary projects cloned and accessible'
        sys.exit(1)


def get_packages_paths(package_tuples):
    paths = []
    for t in package_tuples:
        paths.append(t[0])
    return paths


def get_distribution_codename():
    stdout = StringIO()
    run('python -c "import platform, json, sys; '
        'sys.stdout.write(\'DISTROOPEN{0}DISTROCLOSE\\n\''
        '.format(json.dumps(platform.dist())))"', stdout=stdout)
    stdout = stdout.getvalue()
    jsonres = stdout[stdout.find("DISTROOPEN") + 10:stdout.find("DISTROCLOSE")]
    return json.loads(jsonres)[2]


@contextmanager
def virtualenv(virtual_env_path):
    with prefix('source {0}/bin/activate'.format(virtual_env_path)):
        yield


def upload_agent_to_manager(base_dir, distro):

    """
    see instructions for creating your own agent at http://getcloudify.org
    under Guides - Creating a Cloudify agent.
    """

    put('{0}/{1}-agent.tar.gz'.format(base_dir, distro),
        '/opt/manager/resources/packages/agents/')
    put('{0}/{1}-celeryd-cloudify.init.template'.format(base_dir, distro),
        '/opt/manager/resources/packages/templates/')
    put('{0}/{1}-celeryd-cloudify.conf.template'.format(base_dir, distro),
        '/opt/manager/resources/packages/templates/')
    put('{0}/{1}-agent-disable-requiretty.sh'.format(base_dir, distro),
        '/opt/manager/resources/packages/scripts/')
