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
import json
import contextlib
from datetime import datetime

from fabric import api

from cloudify_rest_client import CloudifyClient


DOCKER_META = 'cfy.json'


def dump():

    mappings = _get_cfy_mappings()

    with logs(mappings) as dump_file:
        dump_file.add_deployments()
        dump_file.add_rest_service()


def _get_cfy_mappings():

    api.sudo('docker inspect cfy > {0}'.format(DOCKER_META))
    api.get(remote_path=DOCKER_META, local_path=DOCKER_META)

    with open(DOCKER_META) as f:
        meta = json.load(f)[0]
    os.remove(DOCKER_META)

    return meta['Volumes']


class Dump(object):

    BASE_DIR = '/tmp'

    def __init__(self, mappings):
        super(Dump, self).__init__()
        self.mappings = mappings
        self.management_ip = api.env.host_string
        self.dir_name = self._generate_dir_name()
        self.dir_path = '{0}/{1}'.format(self.BASE_DIR, self.dir_name)
        self.rest_client = CloudifyClient(host=self.management_ip)
        self.tar_file = '{0}.tar.gz'.format(self.dir_name)

    def _generate_dir_name(self):
        timestamp = str(datetime.now()).replace(' ', '-').replace(':', '.')
        return 'Cloudify-Manager-{0}-{1}-Logs'.format(
            self.management_ip, timestamp)

    def add_deployments(self):

        deployments_dir = '{0}/deployments'.format(self.dir_path)
        api.run('mkdir -p {0}'.format(deployments_dir))

        home_dir = self.mappings['/root']

        def _add_worker(worker_name):

            worker_dir = 'cloudify.{0}'.format(worker_name)

            src = '{0}/{1}/work'.format(
                home_dir,
                worker_dir
            )
            dst = os.path.join(
                deployment_dir,
                worker_dir
            )
            api.sudo('cp -r {0} {1}'.format(src, dst))

        deployments = self.rest_client.deployments.list()
        for deployment in deployments:
            deployment_dir = '{0}/{1}'.format(
                deployments_dir,
                deployment.id
            )
            api.run('mkdir -p {0}'.format(deployment_dir))
            _add_worker(deployment.id)
            _add_worker('{0}_workflows'.format(deployment.id))

    def add_rest_service(self):
        rest_dir = '{0}/rest-service'.format(self.dir_path)
        rest_logs = self.mappings['/var/log/cloudify']
        api.sudo('cp -r {0} {1}'.format(rest_logs, rest_dir))

    def tar(self):
        api.run('cd {0} && tar -zcvf {1} {2}'
                .format(self.BASE_DIR,
                        self.tar_file,
                        self.dir_name))

    def get(self):
        api.get(remote_path='{0}/{1}'.format(self.BASE_DIR,
                                             self.tar_file),
                local_path='{0}'.format(self.tar_file))


@contextlib.contextmanager
def logs(mappings):
    d = Dump(mappings)
    yield d
    d.tar()
    d.get()
