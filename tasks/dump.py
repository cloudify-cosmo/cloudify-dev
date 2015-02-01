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
import logging
from datetime import datetime

from fabric import api

from cloudify_rest_client import CloudifyClient


DOCKER_META = 'cfy.json'


logging.getLogger('cloudify.rest_client.http').setLevel(logging.INFO)


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

    def __init__(self, mappings):
        super(Dump, self).__init__()
        self.management_ip = api.env.host_string
        self.dir_name = self._create_dir_name()
        self.destination = self._create_dir()
        self.mappings = mappings

        self.deployments_dir = os.path.join(
            self.destination, 'deployments'
        )
        self.rest_dir = os.path.join(
            self.destination, 'rest-service'
        )
        self.rest_client = CloudifyClient(host=self.management_ip)

    def _create_dir_name(self):
        timestamp = str(datetime.now()).replace(' ', '-').replace(':', '.')
        return 'Cloudify-Manager-{0}-{1}-Logs'.format(
            self.management_ip, timestamp)

    def _create_dir(self):
        logs_dir = '/tmp/{0}'.format(self.dir_name)
        api.run('mkdir -p {0}'.format(logs_dir))
        return logs_dir

    def add_deployments(self):

        home_dir = self.mappings['/root']
        api.run('mkdir -p {0}'.format(self.deployments_dir))

        def _add_worker(worker_name):
            src = os.path.join(
                home_dir,
                'cloudify.{0}'.format(worker_name),
                'work')
            dst = os.path.join(
                self.deployments_dir,
                deployment.id,
                'cloudify.{0}'.format(worker_name)
            )
            api.sudo('cp -r {0} {1}'.format(src, dst))

        deployments = self.rest_client.deployments.list()
        for deployment in deployments:
            api.run('mkdir -p {0}'.format(
                os.path.join(self.deployments_dir,
                             deployment.id)))
            _add_worker(deployment.id)
            _add_worker('{0}_workflows'.format(deployment.id))

    def add_rest_service(self):
        rest_logs = self.mappings['/var/log/cloudify']
        api.sudo('cp -r {0} {1}'.format(rest_logs, self.rest_dir))

    def tar(self):
        api.run('cd /tmp && tar -zcvf {0}.tar.gz {0}'
                .format(self.dir_name))

    def get(self):
        api.get(remote_path='/tmp/{0}.tar.gz'.format(self.dir_name),
                local_path='{0}.tar.gz'.format(self.dir_name))

@contextlib.contextmanager
def logs(mappings):
    d = Dump(mappings)
    yield d
    d.tar()
    d.get()