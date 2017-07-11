#!/usr/bin/env python

import argparse
import json
import os
import uuid
import shutil
import subprocess
import sys
import time
import uuid

from path import Path
import jinja2


TERRAFORM_TEMPLATE_FILE = 'openstack-env.jinja2.tf'
TERRAFORM_OUTPUT_FILE = 'openstack-env.tf'
WORK_DIR = Path.getcwd() / 'work'
CONFIG_FILE_PATH = 'resources/config.json'
WEIGHTS_FILE_PATH = 'resources/weights.json'
PRIVATE_KEY_FILE = WORK_DIR / 'ssh_key.pem'
PUBLIC_KEY_FILE = WORK_DIR / 'ssh_key.pem.pub'
DEFAULT_PATTERN = 'test_*.py'


# TODO: handle terraform cleanup error (don't remove the work dir!)
# TODO: handle terraform errors (if exit code != 0).
# TODO: excluded tests from config are not processed on simulation

_config = None


def get_configuration():
    global _config
    if _config is None:
        with open(CONFIG_FILE_PATH, 'r') as f:
            _config = json.loads(f.read())
    return _config


def get_cloudify_premium_branch():
    return get_configuration()['repositories']['cloudify-premium']


def validate(args):
    if args.number_of_servers < 1 or args.number_of_servers > 10:
        print('Argument error: number_of_servers accepts a value between 1 to 10')
        sys.exit(1)
    if WORK_DIR.exists():
        print('Validation error: work directory already exists!')
        sys.exit(1)


def create_ssh_keys():
    if os.system("ssh-keygen -t rsa -f {0} -q -N ''".format(
            PRIVATE_KEY_FILE)) != 0:
        raise IOError('Error creating SSH key: {}'.format(
                self.private_key_path))
    if os.system('chmod 400 {0}'.format(PRIVATE_KEY_FILE)) != 0:
        raise IOError('Error setting private key file permission')



def deploy(number_of_servers, pattern, keep_servers):
    print('Creating work directory: {0}'.format(WORK_DIR))
    os.mkdir(WORK_DIR)

    print('Creating SSH keys..')
    create_ssh_keys()

    print('Rendering terraform template..')
    with open(TERRAFORM_TEMPLATE_FILE, 'r') as f:
        terraform_template_content = f.read()

    rendered_template = jinja2.Template(terraform_template_content).render({
        'servers': range(number_of_servers)
    })

    
    output_file = WORK_DIR / TERRAFORM_OUTPUT_FILE    
    with open(output_file, 'w') as f:
        f.write(rendered_template)

    config = get_configuration()

    print('Creating inputs file..')
    inputs = json.dumps({
        "resource_suffix": str(uuid.uuid4()),
        "public_key_path": PUBLIC_KEY_FILE,
        "private_key_path": PRIVATE_KEY_FILE,
        "flavor": config['test_server']['flavor'],
        "image": config['test_server']['image'],
        "tests_pattern": pattern
    }, indent=2)
    print(inputs)

    inputs_file = WORK_DIR / 'inputs.json'
    with open(inputs_file, 'w') as f:
        f.write(inputs)

    print('Copying terraform scripts..')
    source_scripts_dir = os.path.join(os.getcwd(), 'resources')
    destination_scripts_dir = WORK_DIR / 'resources'
    shutil.copytree(source_scripts_dir, destination_scripts_dir)

    with WORK_DIR:
        print('Cloning cloudify-premium..')
        os.system('git clone git@github.com:cloudify-cosmo/cloudify-premium.git -b {0} --depth 1 -q'.format(get_cloudify_premium_branch()))
        print('Packing cloudify-premium to an archive..')
        os.system('tar czf cloudify-premium.tar.gz cloudify-premium')

    print('Creating test servers using terraform..')

    with WORK_DIR:
        os.system('terraform apply -var-file inputs.json')

    if not keep_servers:
        with WORK_DIR:
            os.system('terraform destroy -force -var-file inputs.json')


def get_servers_ip_address():
    cmd = 'terraform output -json'.split(' ')
    with WORK_DIR:
        output = json.loads(subprocess.check_output(cmd))
    ips = []
    for i in xrange(999999):
        key = 'public_ip_address_{0}'.format(i)
        if key in output:
            ips.append(output[key]['value'])
        else:
            return ips
    return ips


def destroy():
    print('Destroying the test environment..')
    with WORK_DIR:
        exit_code = os.system('terraform destroy -force -var-file inputs.json')
    
    if exit_code == 0:
        print('Deleting work dir..')
        shutil.rmtree(WORK_DIR)
        print('Done!')
    else:
        print('Failed to destroy the test environment!')
        sys.exit(exit_code)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    run_parser = subparsers.add_parser('run', help='Run integration tests')
    run_parser.set_defaults(which='run')
    run_parser.add_argument('-n', '--number-of-servers',
                            help='The number of servers to create and distribute the tests to.',
                            type=int, required=True)
    run_parser.add_argument('-p', '--pattern', type=str, required=False, default=DEFAULT_PATTERN,
                            help='Test modules pattern to match (default=test_*.py).')
    run_parser.add_argument('-k', '--keep-servers', action='store_true',
                            help='Keep test servers up (test servers are terminated by default).')

    simulate_parser = subparsers.add_parser('simulate', help='Simulate servers distribution.')
    simulate_parser.set_defaults(which='simulate')
    simulate_parser.add_argument('--repos', required=True,
                                 help='The directory Cloudify repositories are checked-out in.')
    simulate_parser.add_argument('-p', '--pattern', type=str, required=False, default=DEFAULT_PATTERN,
                                 help='Test modules pattern to match (default=test_*.py).')

    create_server_parser = subparsers.add_parser('create-server', help='Creates a test server.')
    create_server_parser.set_defaults(which='create_server')

    destroy_parser = subparsers.add_parser('destroy', help='Destroys the test envrionment.')
    destroy_parser.set_defaults(which='destroy')

    ssh_parser = subparsers.add_parser('ssh', help='SSH to a test server.')
    ssh_parser.add_argument('server_index', nargs='?', default=0, type=int, help='Server index to SSH to.')
    ssh_parser.set_defaults(which='ssh')

    args = parser.parse_args()
    
    start = time.time()

    if args.which == 'run':
        validate(args)
        deploy(args.number_of_servers, args.pattern, args.keep_servers)
        os.system('python create-report.py')

    elif args.which == 'simulate':
        os.system(
            'python resources/run-tests.py --repos {0} --weights-file {1} --config-file {2} --pattern {3} --simulate'.format(
                args.repos, WEIGHTS_FILE_PATH, CONFIG_FILE_PATH, args.pattern))
    elif args.which == 'destroy':
        destroy()
    elif args.which == 'create_server':
        # Hopefully tests will not be found for this pattern.
        deploy(1, pattern=str(uuid.uuid4()), keep_servers=True)
        ip_address = get_servers_ip_address()[0]
        print('Test server is up!')
        print('SSH to it by running: "ssh -i {0} centos@{1}"'.format(PRIVATE_KEY_FILE, ip_address))
        print('Or ./itests.py ssh')
    elif args.which == 'ssh':
        ip_addresses = get_servers_ip_address()
        if args.server_index > len(ip_addresses) - 1 or args.server_index < 0:
            print('Server index not in range! (0:{0})'.format(len(ip_addresses) - 1))
            sys.exit(1)
        os.system('ssh -oStrictHostKeyChecking=no -i {0} centos@{1}'.format(PRIVATE_KEY_FILE, ip_addresses[args.server_index]))
        sys.exit(0)

    elapsed_seconds = float('%.2f' % (time.time() - start))
    print('')
    print('Execution time: {0} seconds.'.format(elapsed_seconds))
