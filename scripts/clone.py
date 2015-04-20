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

REPOSITORIES = [
    'flask-securest',
    'cloudify-cli',
    'cloudify-manager',
    'cloudify-rest-client',
    'cloudify-plugins-common',
    'cloudify-dsl-parser',
    'cloudify-script-plugin',
    'cloudify-openstack-plugin',
    'cloudify-system-tests'
]


def run_command(command):
    os.system(command)


def clone_repo(repo_name):
    repo_url = 'https://github.com/cloudify-cosmo/{0}'\
        .format(repo_name)
    if method:
        if method == 'ssh':
            repo_url = 'git@github.com:cloudify-cosmo/{0}.git'\
                .format(repo_name)
        else:
            raise RuntimeError('Unsupported authentication method ({'
                               '0})'.format(method))
    run_command('git clone {0}'.format(repo_url))


def clone():
    for repo in REPOSITORIES:
        clone_repo(repo)


if __name__ == '__main__':
    if len(sys.argv) == 2:
        method = sys.argv[1]
    clone()
