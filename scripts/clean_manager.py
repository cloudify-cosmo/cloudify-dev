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

import sys

from cloudify_rest_client import CloudifyClient
from cloudify_rest_client.executions import Execution
from cloudify_cli.execution_events_fetcher import wait_for_execution


def events_handler(events):
    for event in events:
        print event


def clean_manager():

    rest = CloudifyClient(host=management_ip)
    deployments = rest.deployments.list()
    blueprints = rest.blueprints.list()

    for deployment in deployments:

        # cancel all running executions
        executions = rest.executions.list(deployment_id=deployment.id)
        for execution in executions:
            if execution.status not in Execution.END_STATES:
                print 'Cancelling execution {0} of deployment {1}'.format(
                    execution.id, deployment.id)
                rest.executions.cancel(execution_id=execution.id, force=True)
                wait_for_execution(
                    client=rest,
                    execution=execution,
                    include_logs=True,
                    events_handler=events_handler)

        # execute uninstall on each deployment
        print 'Running uninstall on deployment {0}'.format(deployment.id)
        uninstall_execution = rest.executions.start(
            deployment_id=deployment.id,
            workflow_id='uninstall')

        # wait for uninstall to finish
        print 'Waiting for uninstall on deployment {0} to finish'.format(
            deployment.id)
        wait_for_execution(client=rest, execution=uninstall_execution,
                           include_logs=True, events_handler=events_handler)

        # delete the deployment
        print 'Deleting deployment {0}'.format(deployment.id)
        rest.deployments.delete(deployment_id=deployment.id)

    for blueprint in blueprints:

        # delete the blueprint
        print 'Deleting blueprint {0}'.format(blueprint.id)
        rest.blueprints.delete(blueprint_id=blueprint.id)


if __name__ == '__main__':
    management_ip = sys.argv[1]
    clean_manager()
