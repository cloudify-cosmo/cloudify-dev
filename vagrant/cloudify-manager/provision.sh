#!/bin/bash -e

EXECUTION_ENV=$1
MANAGER_BLUEPRINTS_BRANCH=$2
CLI_TAG=${MANAGER_BLUEPRINTS_BRANCH}


function _install_prerequisites() {

    sudo ufw disable

    sudo apt-get -y update
    sudo apt-get install -y python-dev

    sudo apt-get install -y git-core
    sudo apt-get install -y curl

    wget https://bootstrap.pypa.io/get-pip.py
    sudo python get-pip.py
    sudo pip install virtualenv
    sudo rm -rf ~/.cache

}

function _install_cfy() {

    virtualenv /home/vagrant/cli-env
    source /home/vagrant/cli-env/bin/activate
    curl --silent --show-error --retry 5 "https://raw.githubusercontent.com/cloudify-cosmo/cloudify-cli/${CLI_TAG}/dev-requirements.txt" -o dev-requirements.txt
    pip install -r dev-requirements.txt "https://github.com/cloudify-cosmo/cloudify-cli/archive/${CLI_TAG}.zip"
    rm dev-requirements.txt

}

function _uninstall_cfy() {

    rm -rf /home/vagrant/cli-env
    rm -rf /home/vagrant/cli-work

}


function _bootstrap() {

    # create the cli working directory
    mkdir /home/vagrant/cli-work
    cd /home/vagrant/cli-work

    cfy init

    # download the appropriate simple manager blueprint file
    curl --silent --show-error --retry 5 "https://raw.githubusercontent.com/cloudify-cosmo/cloudify-manager-blueprints/${MANAGER_BLUEPRINTS_BRANCH}/simple/simple.yaml" -o simple.yaml

    # copy the pre-made inputs to the cli working directory
    cp /vagrant/inputs.json .

    # extract machine IP
    IP=$(/sbin/ifconfig eth1 | grep 'inet addr:' | cut -d: -f2 | awk '{print $1}')

    # inject ip into the inputs file
    sed -i "s/INJECTED_IP/${IP}/g" inputs.json

    cfy bootstrap --install-plugins -p simple.yaml -i inputs.json

    cfy status

}

function development() {
    _install_prerequisites
    _install_cfy
    _bootstrap
    cd /home/vagrant/cli-work
    cfy dev --tasks-file /home/vagrant/cloudify/cloudify-dev/tasks/tasks.py --task setup-dev-env
}


function production() {
    _install_prerequisites
    _install_cfy
    _bootstrap
    _uninstall_cfy
}

${EXECUTION_ENV}