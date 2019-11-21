#!/bin/bash

DOCL_IMAGE_BUILDER_SERVER="10.239.1.189"

set +e

#rm -f /tmp/docl-image-downloaded

echo "# Checking whether docl image can be downloaded directly from build machine.."
curl -I http://${DOCL_IMAGE_BUILDER_SERVER}/docl_images/docl-manager.tar.gz | grep 200

exit_code="$?"
if [ "$exit_code" -eq "0" ]; then
    echo "# Downloading docl image from build machine!.."
    touch /tmp/docl-image-downloaded
    set -e
    curl -O http://${DOCL_IMAGE_BUILDER_SERVER}/docl_images/docl-manager.tar.gz
    echo "# Loading docl image.."
    docker -H 172.20.0.1 load -q -i docl-manager.tar.gz
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
