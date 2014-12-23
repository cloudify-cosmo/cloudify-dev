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
from os.path import dirname
from StringIO import StringIO
from fabric.api import *
from fabric.contrib import files

MANAGER_BRANCH = 'master'

# root of synced folder with cloudify github repositories
CODE_BASE = '/home/vagrant/cloudify'

# path to different cloudify components relative to 'CODE_BASE'
CLOUDIFY_MANAGER = 'cloudify-manager'
MANAGER_REST = 'cloudify-manager/rest-service/manager_rest'
WORKER_INSTALLER = 'cloudify-manager/plugins/agent-installer/worker_installer'
PLUGIN_INSTALLER = 'cloudify-manager/plugins/plugin-installer/plugin_installer'
W_WORKER_INSTALLER = 'cloudify-manager/plugins/windows-agent-installer/windows_agent_installer'
W_PLUGIN_INSTALLER = 'cloudify-manager/plugins/windows-plugin-installer/windows_plugin_installer'
RIEMANN_CONTROLLER = 'cloudify-manager/plugins/riemann-controller/riemann_controller'
SCRIPT_RUNNER = 'cloudify-script-plugin/script_runner'
SYSTEM_WORKFLOWS = 'cloudify-manager/workflows/cloudify_system_workflows'
DSL_PARSER = 'cloudify-dsl-parser/dsl_parser'
CLOUDIFY_COMMON = 'cloudify-plugins-common/cloudify'
REST_CLIENT = 'cloudify-rest-client/cloudify_rest_client'
AMQP_INFLUXDB = 'cloudify-amqp-influxdb/amqp_influxdb'
PACKAGER = 'cloudify-packager'

# agent package details
VIRTUALENV_PACKAGE = '/home/vagrant/package'
VIRTUALENV_PARENT = '{0}/linux'.format(VIRTUALENV_PACKAGE)
VIRTUALENV_PATH = '{0}/env'.format(VIRTUALENV_PARENT)

VIRTUALENV_PATH_MANAGER = '/opt/celery/cloudify.management__worker/env'
VIRTUALENV_PATH_CELERY_MANAGER = '/opt/celery/cloudify.management__worker/env'
MANAGER_PACKAGES_INSTALLED_INDICATOR = '/home/vagrant/manager_packages_installed'

# packages to install (in this order) for the agent package virtual env
AGENT_PACKAGES = [
    dirname(package) for package in [
        REST_CLIENT,
        CLOUDIFY_COMMON,
        WORKER_INSTALLER,
        PLUGIN_INSTALLER,
        W_WORKER_INSTALLER,
        W_PLUGIN_INSTALLER,
        SCRIPT_RUNNER,
    ]
]

MANAGER_PACKAGES = [
    dirname(package) for package in [
        DSL_PARSER,
        MANAGER_REST,
        AMQP_INFLUXDB,
        ]
]

MANAGER_CELERY_PACKAGES = [
    dirname(package) for package in [
        REST_CLIENT,
        CLOUDIFY_COMMON,
        PLUGIN_INSTALLER,
        WORKER_INSTALLER,
        RIEMANN_CONTROLLER,
        SYSTEM_WORKFLOWS,
        ]
]

AGENT_DEPENDENCIES = [
    'celery==3.0.24'
    'pyzmq==14.3.1',
]

# links to host machine source code for the agent virtualenv
AGENT_LINKS = {
    '{0}/lib/python2.7/site-packages'.format(VIRTUALENV_PATH): {
        'cloudify': CLOUDIFY_COMMON,
        'cloudify_rest_client': REST_CLIENT,
        'plugin_installer': PLUGIN_INSTALLER,
        'worker_installer': WORKER_INSTALLER,
        'windows_agent_installer': W_WORKER_INSTALLER,
        'windows_plugin_installer': W_PLUGIN_INSTALLER,
        'script_runner': SCRIPT_RUNNER,
    }
}

MANAGER_RESOURCES_LINKS = {
    '/opt/manager/resources/': {
        'packages/scripts': '{0}/package-configuration/ubuntu-agent'.format(PACKAGER),
        'packages/templates': '{0}/package-configuration/ubuntu-agent'.format(PACKAGER),
        'cloudify': '{0}/resources/rest-service/cloudify'.format(CLOUDIFY_MANAGER)
    }
}

# services to stop (and start in reverse order) when starting (and ending)
# setup_env task
managed_services = [
    'manager',
    'celeryd-cloudify-management',
    'amqpflux',
    'riemann',
]


def setup_dev_env(link_manager=True):
    _validate_source_path()
    link_source(link_manager)
    update_agent_package()
    restart_services()


def link_source(link_manager=True):
    _validate_source_path()
    if link_manager:
        if not files.exists(MANAGER_PACKAGES_INSTALLED_INDICATOR):
            with virtualenv(VIRTUALENV_PATH_MANAGER):
                for package_name in MANAGER_PACKAGES:
                    _pip_install('-e {0}/{1}'.format(CODE_BASE, package_name))
            with virtualenv(VIRTUALENV_PATH_CELERY_MANAGER):
                for package_name in MANAGER_CELERY_PACKAGES:
                    _pip_install('-e {0}/{1}'.format(CODE_BASE, package_name))
            run('touch {}'.format(MANAGER_PACKAGES_INSTALLED_INDICATOR))
        _link(MANAGER_RESOURCES_LINKS)


def update_agent_package():
    _validate_source_path()
    if files.exists(VIRTUALENV_PARENT):
        run('rm -rf {0}'.format(VIRTUALENV_PARENT))
    run('mkdir -p {0}'.format(VIRTUALENV_PARENT))
    run('virtualenv {0}'.format(VIRTUALENV_PATH))
    with virtualenv(VIRTUALENV_PATH):
        for dependency in AGENT_DEPENDENCIES:
            _pip_install(dependency)
        for package_name in AGENT_PACKAGES:
            _pip_install('{0}/{1}'.format(CODE_BASE, package_name))
    _link(AGENT_LINKS)
    run('tar czf package.tar.gz package --dereference')
    agent_package_path = '/opt/manager/resources/packages/agents/Ubuntu-{0}-agent.tar.gz' \
        .format(get_distribution_codename())
    sudo('cp package.tar.gz {0}'.format(agent_package_path))
    run('rm package.tar.gz')


def restart_services():
    stop_services()
    start_services()


def stop_services():
    for service in managed_services:
        sudo('stop {}'.format(service))


def start_services():
    for service in managed_services[::-1]:
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


def _pip_install(python_package):
    run('pip install {0}'.format(python_package))


def _validate_source_path():
    stdout = StringIO()
    run('ls -l {0}'.format(CODE_BASE), stdout=stdout)
    cloudify_projects = stdout.getvalue()
    all_packages = AGENT_PACKAGES.extend(MANAGER_PACKAGES).extend(MANAGER_CELERY_PACKAGES)
    missing_projects = []
    for package_name in all_packages:
        directory = package_name[:package_name.find('/')]
        if directory not in cloudify_projects:
            missing_projects.append(directory)
    if missing_projects:
        print '\e[31mCannot link source. Missing projects detected on host machine: {0}'\
            .format(os.linesep.join(missing_projects))
        print '\e[31mMake sure you have all the necessary projects cloned and accessible'
        sys.exit(1)


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
