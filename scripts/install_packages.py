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
PACKAGES = [

    # This order is important, do not change unless
    # you know what you are doing.

    'cloudify-common/',
    'cloudify-cli/',
    'cloudify-manager/plugins/agent-installer/',
    'cloudify-manager/plugins/plugin-installer/',
    'cloudify-manager/plugins/riemann-controller/',
    'cloudify-manager/workflows/',
    'cloudify-manager/rest-service/'
]


def run_command(command):
    os.system(command)


def install_package(package):
    run_command('{0}/pip install -e {1}'
                .format(BIN_PATH, package))


def install():
    for package in PACKAGES:
        install_package(package)


if __name__ == '__main__':
    install()
