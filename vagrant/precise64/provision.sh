#!/bin/bash -e

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

_install_prerequisites