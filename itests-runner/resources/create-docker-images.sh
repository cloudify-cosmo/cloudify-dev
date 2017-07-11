#!/bin/bash

set +e

echo "# Checking whether docl image can be downloaded directly from build machine.."
curl -I http://10.239.2.51/docl_images/centos-manager.tar | grep 200

exit_code="$?"
if [ "$exit_code" -eq "0" ]; then
    echo "# Downloading docl image from build machine!.."
    set -e
    curl -O http://10.239.2.51/docl_images/centos-manager.tar
    echo "# Loading docl image.."
    gunzip -c centos-manager.tar | docker -H 172.20.0.1 load -q
else
    echo "# docl image is not available for download from build machine, it will be downloaded from S3 :-("
fi

echo "# Building CentOS 7 docker image.."
set +e
docker -H 172.20.0.1 images | grep "cloudify/centos[[:space:]]*7"
if [ "$?" -ne "0" ]; then
    set -e
    pushd repos/docl/docl/resources > /dev/null
        docker -H 172.20.0.1 build -q -t cloudify/centos:7 .
    popd > /dev/null
else
    echo "# CentOS 7 docker image already exists!"
fi

set -e
