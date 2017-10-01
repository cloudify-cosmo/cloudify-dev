########
# Copyright (c) 2017 GigaSpaces Technologies Ltd. All rights reserved
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
import codecs
from setuptools import setup

setup(
    name='clap',
    version='0.1.0',
    author='Gigaspaces',
    author_email='cosmo-admin@gigaspaces.com',
    license='Apache 2.0',
    platforms='All',
    description='Easy git mgmt',
    py_modules=['clap'],
    include_package_data=True,
    zip_safe=False,
    entry_points={'console_scripts': ['clap = clap:main']},
    install_requires=[
        'argh',
        'sh',
        'gitpython',
        'colorama'
    ],
)
