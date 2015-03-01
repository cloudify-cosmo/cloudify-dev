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

import os
import sys

BIN_PATH = os.path.dirname(sys.executable)


class CloudifyPackage(object):

    def __init__(self, package_name, package_path=None, repo_name=None):
        super(CloudifyPackage, self).__init__()
        self.package_name = package_name
        self.package_path = package_path or package_name
        self.repo_name = repo_name or package_name


class CorePackage(CloudifyPackage):
    pass


class PluginPackage(CloudifyPackage):
    pass


class NonPythonPackage(CloudifyPackage):
    pass


CLOUDIFY_PACKAGES = [

    # This order is important, do not change unless
    # you know what you are doing.
    CorePackage(package_name='cloudify-rest-client'),
    CorePackage(package_name='cloudify-dsl-parser'),
    CorePackage(package_name='cloudify-plugins-common'),

    PluginPackage(package_name='cloudify-script-plugin'),
    PluginPackage(package_name='cloudify-fabric-plugin'),
    PluginPackage(package_name='cloudify-openstack-plugin'),
    PluginPackage(package_name='cloudify-diamond-plugin'),

    CorePackage(package_name='cloudify',
                package_path='cloudify-cli',
                repo_name='cloudify-cli'),
    CorePackage(package_name='cloudify-agent-installer-plugin',
                package_path='cloudify-manager/plugins/agent-installer',
                repo_name='cloudify-manager'),
    CorePackage(package_name='cloudify-plugin-installer-plugin',
                package_path='cloudify-manager/plugins/plugin-installer',
                repo_name='cloudify-manager'),
    CorePackage(package_name='cloudify-riemann-controller-plugin',
                package_path='cloudify-manager/plugins/riemann-controller',
                repo_name='cloudify-manager'),
    CorePackage(package_name='cloudify-workflows',
                package_path='cloudify-manager/workflows/',
                repo_name='cloudify-manager'),
    CorePackage(package_name='cloudify-rest-service',
                package_path='cloudify-manager/rest-service/',
                repo_name='cloudify-manager'),
    CorePackage(package_name='cloudify-system-tests'),

    NonPythonPackage(package_name=None,
                     package_path='cloudify-manager-blueprints')
]


def run_command(command, wd=None):
    current_cwd = os.getcwd()
    if not wd:
        wd = current_cwd
    try:
        os.chdir(wd)
        os.system(command)
    finally:
        os.chdir(current_cwd)


def switch_version(package, version):
    print 'Switching version of package {0}'.format(package.package_name)
    run_command('git fetch', package.repo_name)
    run_command('git pull --tags', package.repo_name)
    run_command('git checkout {0}'.format(version),
                package.repo_name)
    if not isinstance(package, NonPythonPackage):
        run_command('{0}/pip install -e {1}'
                    .format(BIN_PATH, package.package_path))


def switch_versions():
    for package in CLOUDIFY_PACKAGES:
        if isinstance(package, CorePackage):
            switch_version(package, core_version)
        if isinstance(package, PluginPackage):
            switch_version(package, plugins_version)

if __name__ == '__main__':
    core_version = sys.argv[1]
    plugins_version = sys.argv[2]
    switch_versions()
