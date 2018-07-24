#!/bin/bash

set -e

function install_package {
    set +e
    rpm -q $1 > /dev/null
    EXIT_CODE=$?
    set -e
    if [ ! ${EXIT_CODE} -eq 0 ]; then
        echo "Installing $1.."
        sudo yum install $1 -y -q
    else
        echo "$1 is already installed!"
    fi
}

echo "# Installing system dependencies.."
install_package docker
install_package bridge-utils
install_package gcc
install_package python-devel
install_package git
install_package openssl-devel
install_package openldap-devel
install_package gcc-c++

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

echo "# Creating docker images in a sub-process.."
nohup /tmp/create-docker-images.sh > create-docker-images.log 2>&1 &
create_docker_images_pid=$!

echo "# Downloading and configuring clap..."
curl https://raw.githubusercontent.com/cloudify-cosmo/cloudify-dev/master/scripts/clap -o /tmp/clap
chmod +x /tmp/clap
pip install sh==1.11 argh==0.26.2 colorama==0.3.3

mkdir -p ~/dev/repos

echo "# Unpacking cloudify-premium.."
# This is in order to avoid having credentials for private repos
# -m is for suppressing timestamp related warnings
tar xzf /tmp/cloudify-premium.tar.gz -C ~/dev/repos -m

echo "# Creating clap requirements file..."
# This will create /tmp/clap-requirements.txt
/tmp/create-clap-requirements.py

echo "# Cloning/installing required repositories.."
/tmp/clap setup --requirements=/tmp/clap-requirements.txt

echo "Installing pytest.."
pip install -q pytest

echo "# Installing pyaml==3.10.."
pip install -q pyyaml==3.10 --upgrade

echo "# Initializing docl.."
docl init --docker-host 172.20.0.1 --source-root=$HOME/dev/repos --ssh-key-path=$HOME/.ssh/id_rsa

# If this file wasn't touched, we need to download the image from S3
if [ ! -f /tmp/docl-image-downloaded ]; then
    echo "# Downloading docl image from build server failed. Image will be pulled from S3.."
    echo "# Pulling docl image.."
    docl pull-image --no-progress
fi

echo "source ~/venv/bin/activate" >> ~/.bashrc
echo "export DOCKER_HOST=172.20.0.1" >> ~/.bashrc

echo "# Waiting for docker images creation..."
wait $create_docker_images_pid
cat create-docker-images.log

echo "# Environment prepared successfully!"
