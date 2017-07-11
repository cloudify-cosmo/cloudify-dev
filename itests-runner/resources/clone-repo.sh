#!/bin/bash

set -e

# $1 - repository name
# $2 - branch name

git clone https://github.com/cloudify-cosmo/$1.git -b $2 --depth 1 -q

