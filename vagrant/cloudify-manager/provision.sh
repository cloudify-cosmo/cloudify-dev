#!/bin/bash -e

EXECUTION_ENV=$1
MANAGER_BLUEPRINTS_BRANCH=$2
CLI_BRANCH=$3
USE_TARZAN=$4

TARZAN_PREFIX="http:\/\/192.168.10.13\/builds\/GigaSpacesBuilds\/cloudify3"

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
    echo "Installing cloudify-cli from ${CLI_BRANCH} branch"
    curl --show-error --retry 5 "https://raw.githubusercontent.com/cloudify-cosmo/cloudify-cli/${CLI_BRANCH}/dev-requirements.txt" -o dev-requirements.txt
    pip install -r dev-requirements.txt "https://github.com/cloudify-cosmo/cloudify-cli/archive/${CLI_BRANCH}.zip"
    rm dev-requirements.txt
}

function _modify_bashrc() {

    echo "cd /home/vagrant/cli-work" >> ~/.bashrc
    echo "source /home/vagrant/cli-env/bin/activate" >> ~/.bashrc
}

function _uninstall_cfy() {

    rm -rf /home/vagrant/cli-env
    rm -rf /home/vagrant/cli-work
}

function _bootstrap() {

    machine_name=$1
    docker=$2

    blueprint_name="simple.yaml"
    blueprint_url="https://raw.githubusercontent.com/cloudify-cosmo/cloudify-manager-blueprints/${MANAGER_BLUEPRINTS_BRANCH}/simple-manager-blueprint.yaml"
    # if [ "${docker}" = true ]; then
    #     blueprint_name="simple-docker.yaml"
    #     blueprint_url="https://raw.githubusercontent.com/cloudify-cosmo/cloudify-manager-blueprints/${MANAGER_BLUEPRINTS_BRANCH}/simple-docker.yaml"
    # fi

    echo "Using blueprint url: ${blueprint_url}"
    echo "Using blueprint name: ${blueprint_name}"

    # create the cli working directory
    mkdir /home/vagrant/cli-work
    cd /home/vagrant/cli-work

    cfy init

    # download the appropriate simple manager blueprint file
    curl --silent --show-error --retry 5 "${blueprint_url}" -o ${blueprint_name}

    # replace url to point to tarzan if specified
    if [ "${USE_TARZAN}" = "YES" ]; then
       sed -i "s/http:\/\/gigaspaces-repository-eu.s3.amazonaws.com\/org\/cloudify3/${TARZAN_PREFIX}/g" ${blueprint_name}
    fi

    # copy the pre-made inputs to the cli working directory
    cp /vagrant/inputs.yaml .

    # extract machine IP
    IP=$(/sbin/ifconfig eth1 | grep 'inet addr:' | cut -d: -f2 | awk '{print $1}')
    # inject ip into the inputs file
    sed -i "s/INJECTED_IP/${IP}/g" inputs.yaml

    # inject machine name (used for key path)
    sed -i "s/INJECTED_MACHINE_NAME/${machine_name}/g" inputs.yaml

    cfy bootstrap --install-plugins -p ${blueprint_name} -i inputs.yaml

    cfy status

}

function dev_packages() {

    _install_prerequisites
    _install_cfy
    _bootstrap dev_packages false
    _modify_bashrc
    cd /home/vagrant/cli-work
    cfy dev --tasks-file /home/vagrant/cloudify/cloudify-dev/tasks/tasks.py --task setup-dev-env
}


function prod_packages() {

    _install_prerequisites
    _install_cfy
    _bootstrap prod_packages false
    _uninstall_cfy
}


function prod_docker() {

    _install_prerequisites
    _install_cfy
    _bootstrap prod_docker true
    _uninstall_cfy
}

${EXECUTION_ENV}
