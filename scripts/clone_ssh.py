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

REPOSITORIES = [
    'cloudify-cli',
    'cloudify-manager',
    'cloudify-rest-client',
    'cloudify-plugins-common',
    'cloudify-dsl-parser',
    'cloudify-script-plugin'
]


def run_command(command):
    os.system(command)


def clone_repo(repo_name):
    run_command('git clone git@github.com:cloudify-cosmo/{0}.git'.format(repo_name))


def clone():
    for repo in REPOSITORIES:
        clone_repo(repo)


if __name__ == '__main__':
    clone()
