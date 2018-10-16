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

# This script is used to sync most of the common cloudify packages
# on a running manager

if [ $# -eq 0 ]; then
    echo "Need to provide an IP for the script to work"
    exit 1
fi

IP=$1
USER=${2:-centos}               # Set the default remote (ssh) user
KEY=${3:-~/.ssh/id_rsa}       # Set the default ssh key
REPOS_DIR=${4:-~/dev/repos}   # Set the default local repos folder
MGMTWORKER_DIR=/opt/mgmtworker/env/lib/python2.7/site-packages
MANAGER_DIR=/opt/manager/env/lib/python2.7/site-packages
AGENTS_DIR=/opt/manager/resources/packages/agents
AGENT_DIR=${AGENTS_DIR}/cloudify/env/lib/python2.7/site-packages

function print_line() {

  LINE=$1

  echo
  echo '======================================================================'
  echo $LINE
  echo '======================================================================'
  echo
}


print_line "Chowning folders"
ssh ${USER}@${IP} -i ${KEY} 'sudo chown -R ${USER}:${USER} /opt/mgmtworker/env/lib/python2.7/site-packages'
ssh ${USER}@${IP} -i ${KEY} 'sudo chown -R ${USER}:${USER} /opt/manager/env/lib/python2.7/site-packages'
ssh ${USER}@${IP} -i ${KEY} 'sudo chown -R ${USER}:${USER} /opt/manager/resources/cloudify'
ssh ${USER}@${IP} -i ${KEY} 'sudo chown -R ${USER}:${USER} /opt/manager/resources/spec'

print_line "Syncing mgmtworker packages"
rsync -avz ${REPOS_DIR}/cloudify-common/cloudify ${USER}@${IP}:${MGMTWORKER_DIR} --exclude '*.pyc' --exclude 'test*' -e "ssh -i ${KEY}"
rsync -avz ${REPOS_DIR}/cloudify-agent/cloudify_agent ${USER}@${IP}:${MGMTWORKER_DIR} --exclude '*.pyc' --exclude 'test*' -e "ssh -i ${KEY}"
rsync -avz ${REPOS_DIR}/cloudify-common/cloudify_rest_client ${USER}@${IP}:${MGMTWORKER_DIR} --exclude '*.pyc' -e "ssh -i ${KEY}"
rsync -avz ${REPOS_DIR}/cloudify-manager/workflows/cloudify_system_workflows ${USER}@${IP}:${MGMTWORKER_DIR} --exclude '*.pyc' -e "ssh -i ${KEY}"

print_line "Syncing manager packages"
rsync -avz ${REPOS_DIR}/cloudify-agent/cloudify_agent ${USER}@${IP}:${MANAGER_DIR} --exclude '*.pyc' --exclude 'test*' -e "ssh -i ${KEY}"
rsync -avz ${REPOS_DIR}/cloudify-common/cloudify_rest_client ${USER}@${IP}:${MANAGER_DIR} --exclude '*.pyc' -e "ssh -i ${KEY}"
rsync -avz ${REPOS_DIR}/cloudify-premium/cloudify_premium ${USER}@${IP}:${MANAGER_DIR} --exclude '*.pyc' -e "ssh -i ${KEY}"
rsync -avz ${REPOS_DIR}/cloudify-manager/rest-service/manager_rest ${USER}@${IP}:${MANAGER_DIR} --exclude '*.pyc' --exclude 'test*' -e "ssh -i ${KEY}"
rsync -avz ${REPOS_DIR}/cloudify-common/dsl_parser ${USER}@${IP}:${MANAGER_DIR} --exclude '*.pyc' --exclude 'test*' -e "ssh -i ${KEY}"

print_line "Syncing resources folder"
rsync -avz ${REPOS_DIR}/cloudify-manager/resources/rest-service/cloudify ${USER}@${IP}:/opt/manager/resources --exclude '*.pyc' -e "ssh -i ${KEY}"
rsync -avz ${REPOS_DIR}/cloudify-manager/resources/rest-service/cloudify/types/types.yaml ${USER}@${IP}:/opt/manager/resources/spec/cloudify/*/ -e "ssh -i ${KEY}"

print_line "Restarting services"
ssh ${USER}@${IP} -i ${KEY} 'sudo systemctl restart cloudify-mgmtworker'
ssh ${USER}@${IP} -i ${KEY} 'sudo systemctl restart cloudify-restservice'

print_line "Repackaging the agent package"
ssh ${USER}@${IP} -i ${KEY} 'cd /opt/manager/resources/packages/agents; sudo tar -xf centos-core-agent.tar.gz'
ssh ${USER}@${IP} -i ${KEY} 'sudo chown -R ${USER}:${USER} /opt/manager/resources/packages/agents/cloudify'

rsync -avz ${REPOS_DIR}/cloudify-common/cloudify ${USER}@${IP}:${AGENT_DIR} --exclude '*.pyc' --exclude 'test*' -e "ssh -i ${KEY}"
rsync -avz ${REPOS_DIR}/cloudify-agent/cloudify_agent ${USER}@${IP}:${AGENT_DIR} --exclude '*.pyc' --exclude 'test*' -e "ssh -i ${KEY}"
rsync -avz ${REPOS_DIR}/cloudify-common/cloudify_rest_client ${USER}@${IP}:${AGENT_DIR} --exclude '*.pyc' -e "ssh -i ${KEY}"
rsync -avz ${REPOS_DIR}/cloudify-diamond-plugin/diamond_agent ${USER}@${IP}:${AGENT_DIR} --exclude '*.pyc' -e "ssh -i ${KEY}"
rsync -avz ${REPOS_DIR}/cloudify-diamond-plugin/cloudify_handler ${USER}@${IP}:${AGENT_DIR} --exclude '*.pyc' -e "ssh -i ${KEY}"

ssh ${USER}@${IP} -i ${KEY} 'sudo chown -R cfyuser:cfyuser /opt/manager/resources/packages/agents/cloudify'
ssh ${USER}@${IP} -i ${KEY} 'cd /opt/manager/resources/packages/agents; sudo tar -czf centos-core-agent.tar.gz cloudify'
ssh ${USER}@${IP} -i ${KEY} 'sudo chown cfyuser:cfyuser /opt/manager/resources/packages/agents/centos-core-agent.tar.gz'
