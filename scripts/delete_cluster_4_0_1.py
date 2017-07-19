#!/usr/bin/env python
"""Script used to remove Cloudify cluster components.

Use this after running `cfy teardown` on a 4.0.0 or 4.0.1 manager, to
also remove cluster-related things.

Do not attempt to run this script without leaving the cluster first.
(unless this is run on the only node in a 1-node cluster)

Note that this script must be run with sudo.
"""

import os
import shutil
import subprocess

config = {
    'services': ['check-runner', 'consul-watcher', 'consul-recovery-watcher',
                 'handler-runner', 'iptables-restore'],
    'postgresql': {
        'data_dir': '/var/pgdata'
    },
    'syncthing': {
        'user': 'cfyuser_syncthing',
        'group': 'syncthing'
    },
    'consul': {
        'user': 'cfyuser_consul',
        'group': 'cfyuser_consul'
    },
    'group': 'cluster'
}


def _stop_systemd_unit(name, ignore_failures=True):
    try:
        subprocess.check_call(['systemctl', 'stop', name])
        subprocess.check_call(['systemctl', 'disable', name])
        os.unlink(os.path.join('/usr/lib/systemd/system',
                               '{0}.service'.format(name)))
    except subprocess.CalledProcessError:
      if not ignore_failures:
          raise


def _userdel(username, ignore_failures=True):
    try:
        subprocess.check_call(['userdel', '--force', username])
    except subprocess.CalledProcessError:
        if not ignore_failures:
            raise


def _groupdel(group, ignore_failures=True):
    try:
        subprocess.check_call(['groupdel', group])
    except subprocess.CalledProcessError:
        if not ignore_failures:
            raise


def _delete_database(config):
    _stop_systemd_unit('cloudify-postgresql')
    try:
        shutil.rmtree(config['postgresql']['data_dir'])
    except:
        pass


def _delete_consul(config):
    for unit in config['services']:
        _stop_systemd_unit('cloudify-{0}'.format(unit))
    _userdel(config['consul']['user'])
    _groupdel(config['consul']['group'])

    # also remove the cluster group here
    _groupdel(config['group'])


def _delete_syncthing(config):
    _userdel(config['syncthing']['user'])
    _groupdel(config['syncthing']['group'])


_delete_syncthing(config)
_delete_database(config)
_delete_consul(config)
