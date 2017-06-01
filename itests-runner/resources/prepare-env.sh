#!/bin/bash

set -e

echo "# Installing system dependencies.."
sudo yum install docker bridge-utils gcc python-devel git -y -q

echo "# Creating a network bridge.."
sudo brctl addbr cfy0
sudo ip addr add 172.20.0.1/24 dev cfy0
sudo ip link set dev cfy0 up

echo "# Updating docker service file to use the network bridge.."
sudo /usr/bin/sed -i -e "s/OPTIONS=.*/OPTIONS='--mtu=1450 --bridge cfy0 --host 172.20.0.1 --selinux-enabled --log-driver=journald --signature-verification=false'/" /etc/sysconfig/docker

echo "# Starting docker.."
sudo systemctl start docker

echo "# Installing latest pip.."
curl -O https://bootstrap.pypa.io/get-pip.py
sudo python get-pip.py

echo "# Installing virtualenv.."
sudo pip install -q virtualenv

echo "# Creating virtualenv.."
virtualenv venv
source venv/bin/activate

echo "# Upgrading to latest pip.."
pip install pip -q --upgrade

# This is required as otherwise networkx will fail to install
echo "# Installing six.."
pip install six -q

echo "# Creating a private SSH key.."
ssh-keygen -t rsa -f ~/.ssh/id_rsa -q -N ''
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys

echo "# Cloning required repositories.."
mkdir -p repos

function clone_repo {
    # $1 - repository name
    branch=$(python -c "import json; print(json.loads(open('/tmp/config.json', 'r').read())['repositories']['$1'])")
    echo "# Cloning $1.. [$branch]"
    git clone https://github.com/cloudify-cosmo/$1.git -b $branch --depth 1 -q
}

pushd repos
    clone_repo "cloudify-dsl-parser"
    clone_repo "cloudify-rest-client"
    clone_repo "cloudify-plugins-common"
    clone_repo "cloudify-diamond-plugin"
    clone_repo "cloudify-script-plugin"
    clone_repo "cloudify-agent"
    clone_repo "cloudify-cli"
    clone_repo "cloudify-manager"
    clone_repo "cloudify-manager-blueprints"
    clone_repo "cloudify-amqp-influxdb"
    clone_repo "docl"
popd 

echo "# Unpacking cloudfiy-premium.."
# -m is for supressing timestamp related warnings
tar xzf /tmp/cloudify-premium.tar.gz -C ~/repos -m

function pip_install {
    pushd $1
        pip install -q -e .
    popd
}

echo "# Installing dependencies.."
pushd repos
    pip_install "cloudify-dsl-parser"
    pip_install "cloudify-rest-client"
    pip_install "cloudify-plugins-common"
    pip_install "cloudify-cli"
    pip_install "cloudify-manager/rest-service"
    pip_install "cloudify-manager/plugins/riemann-controller"
    pip_install "cloudify-premium"
    pip_install "docl"
    pip_install "cloudify-manager/tests"   
popd    

echo "Installing nose.."
pip install -q nose

echo "# Installing pyaml==3.10.."
pip install -q pyyaml==3.10 --upgrade

echo "# Initializing docl.."
docl init --simple-manager-blueprint-path=$HOME/repos/cloudify-manager-blueprints/simple-manager-blueprint.yaml --docker-host 172.20.0.1 --source-root=$HOME/repos --ssh-key-path=$HOME/.ssh/id_rsa

set +e
curl -O http://10.239.2.51/docl_images/centos-manager.tar
exit_code="$?"
set - e
if [ "$exit_code" -ne "0" ]; then
    echo "# Downloading docl image from build server failed. Image will be pulled from S3.."
    echo "# Pulling docl image.."
    docl pull-image --no-progress
else
    echo "# Loading docl image.."
    gunzip -c centos-manager.tar | docker -H 172.20.0.1 load -q
fi

echo "# Building centos7 docker image.."
set +e
docker -H 172.20.0.1 images | grep "cloudify/centos[[:space:]]*7"
if [ "$?" -ne "0" ]; then
    set -e
    pushd repos/docl/docl/resources
    docker -H 172.20.0.1 build -q -t cloudify/centos:7 .
else
    echo "# centos7 docker image already exists!"
fi

set -e

echo "source ~/venv/bin/activate" >> ~/.bashrc

echo "# Environment prepared successfully!"
