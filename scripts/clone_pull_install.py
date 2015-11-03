########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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
#

import os
import subprocess
import sys

MAIN_REPOS_BRANCH = 'master'
PLUGIN_REPOS_BRANCH = 'master'
FLASK_SECUREST_TAG = '0.7'

BIN_PATH = os.path.dirname(sys.executable)

protocol = None


INSTALL_PACKAGES = [
    'cloudify-rest-client',
    'cloudify-dsl-parser',
    'cloudify-plugins-common',
    'cloudify-script-plugin',
    'cloudify-cli',
    'cloudify-manager/plugins/riemann-controller',
    'cloudify-manager/workflows',
    'cloudify-diamond-plugin',
    'cloudify-agent',
    'cloudify-manager/tests',
    'flask-securest',
    'cloudify-manager/rest-service',
    'cloudify-fabric-plugin',
    'cloudify-openstack-plugin',
    'cloudify-system-tests',
]


UNINSTALL_PACKAGES = [
    'cloudify-rest-client',
    'cloudify-dsl-parser',
    'cloudify-plugins-common',
    'cloudify-script-plugin',
    'cloudify',
    'cloudify-agent',
    'cloudify-riemann-controller-plugin',
    'cloudify-workflows',
    'cloudify-diamond-plugin',
    'cloudify-integration-tests',
    'Flask-SecuREST',
    'cloudify-rest-service',
    'cloudify-fabric-plugin',
    'cloudify-openstack-plugin',
    'cloudify-system-tests',
]


MAIN_REPOS = [
    'cloudify-packager',
    'cloudify-rest-client',
    'cloudify-dsl-parser',
    'cloudify-plugins-common',
    'cloudify-cli',
    'cloudify-agent',
    'cloudify-manager',
    'cloudify-system-tests',
    'cloudify-manager-blueprints',
    'cloudify-nodecellar-example',
]

PLUGIN_REPOS = [
    'cloudify-script-plugin',
    'cloudify-diamond-plugin',
    'cloudify-fabric-plugin',
    'cloudify-openstack-plugin',
]

TAGGED_REPOS = {
    'flask-securest': FLASK_SECUREST_TAG,
}


def run_command(command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    if out:
        print out
    if err:
        print "ERROR: ", err
        sys.exit()


def verify_current_branch(target_branch_name):
    proc = subprocess.Popen('git status', stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    if out:
        if 'On branch {0}'.format(target_branch_name) in out:
            return True
        else:
            return False
    elif err:
        print "ERROR: ", err
        sys.exit()
    else:
        print 'failed to verify current branch, exiting'
        sys.exit()


def pull_repo(repo_path, target_branch_name='master'):

    pwd = os.getcwd()
    os.chdir(repo_path)
    if not verify_current_branch(target_branch_name):
        run_command("git fetch")
        run_command("git checkout '{0}'".format(target_branch_name))
        if not verify_current_branch(target_branch_name):
            print "failed to switch to '{0}', exiting".format(
                target_branch_name)
            sys.exit()
    run_command('git pull origin {0}'.format(target_branch_name))
    os.chdir(pwd)


def fetch_tag(repo_path, repo_tag):
    pwd = os.getcwd()
    os.chdir(repo_path)
    run_command('git fetch --tags')
    run_command('git checkout {0}'.format(repo_tag))
    os.chdir(pwd)


def git_clone(repo):
    if protocol == 'ssh':
        repo_url = 'git@github.com:cloudify-cosmo/{0}.git'.format(repo)
    else:
        repo_url = 'https://github.com/cloudify-cosmo/{0}.git'.format(repo)

    print "local repo doesn't exist, cloning from {0} ...".format(repo_url)
    run_command('git clone {0}'.format(repo_url))


def clone_repos(repos_list):
    for repo in repos_list:
        print '\n'
        print '------------------ CLONING {0} ------------------'.format(repo)
        if os.path.isdir(repo):
            print 'repo exists, skipping ...'
        else:
            git_clone(repo)


def clone_all():
    clone_repos(MAIN_REPOS)
    clone_repos(PLUGIN_REPOS)
    clone_repos(TAGGED_REPOS)


def pull_repos(repos_list, branch_name):
    for repo in repos_list:
        print '\n'
        print '------------------ PULLING {0} ({1}) ------------------'.format(
            repo, branch_name)
        if os.path.isdir(repo):
            pull_repo(repo, branch_name)
        else:
            print '!! pull aborted, local repo not found: {0} !!'.format(repo)
            sys.exit()


def fetch_tagged_repos():
    for repo, tag in TAGGED_REPOS.iteritems():
        print '\n'
        print '------------------ FETCHING {0} ------------------'.format(repo)
        if os.path.isdir(repo):
            fetch_tag(repo, tag)
        else:
            print '!! pull aborted, local repo not found'
            sys.exit()


def uninstall_package(package):
    print '\n'
    print '------------------ UN-INSTALLING {0} ------------------'.format(package)
    run_command('pip uninstall -y {0}'.format(package))


def install_package(package):
    print '\n'
    print '------------------ INSTALLING {0} ------------------'.format(package)
    run_command('{0}/pip install -e {1}'.format(BIN_PATH, package))


def uninstall_all():
    for package in UNINSTALL_PACKAGES:
        uninstall_package(package)


def install_all():
    for package in INSTALL_PACKAGES:
        install_package(package)


if __name__ == '__main__':
    for arg in sys.argv:
        if arg in ('https', 'HTTPS'):
            print 'setting protocol to: https'
            protocol = 'https'
            break

    if not protocol:
        protocol = 'ssh'

    clone_all()
    print '\n\n'
    print '############## CLONE COMPLETED, PULLING ##############'
    print ''
    pull_repos(MAIN_REPOS, MAIN_REPOS_BRANCH)
    pull_repos(PLUGIN_REPOS, PLUGIN_REPOS_BRANCH)
    fetch_tagged_repos()

    print '\n\n'
    print '############## PULL COMPLETED, UN-INSTALLING ##############'
    print ''
    uninstall_all()

    print '\n\n'
    print '############## CLEAN COMPLETED, INSTALLING ##############'
    print ''
    install_all()
