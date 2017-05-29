#!/opt/manager/env/bin/python
"""Uninstall Cloudify Manager cluster services.

This script will remove the cluster services, allowing you to run
`cfy cluster start` (or join) again. This is useful only for development,
when you want to speed up working on the cluster configuration, or when
you passed the wrong flag (eg --cluster-host-ip) and want to try again.

DO NOT USE THIS IN PRODUCTION ENVIRONMENTS. This is NOT an official
"leave the cluster but stay active" script. Things might and will break,
including agents connected to the cluster.
"""

import os
import shutil
import subprocess
from cloudify_premium.ha import (checks,
                                 consul,
                                 utils,
                                 services,
                                 database,
                                 watch_handlers,
                                 syncthing)

config = {
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


def _stop_systemd_unit(name, ignore_failure=True):
    try:
        subprocess.check_call(['systemctl', 'stop', name])
        subprocess.check_call(['systemctl', 'disable', name])
    except subprocess.CalledProcessError:
        if not ignore_failure:
            raise


def _userdel(username, ignore_failure=True):
    try:
        subprocess.check_call(['userdel', '--force', username])
    except subprocess.CalledProcessError:
        if not ignore_failure:
            raise


def _groupdel(group, ignore_failure=True):
    try:
        subprocess.check_call(['groupdel', group])
    except subprocess.CalledProcessError:
        if not ignore_failure:
            raise


def _delete_database(config):
    _stop_systemd_unit('cloudify-postgresql')
    db_service = database.Database()
    try:
        db_service.stop()
        db_service.disable()
    except subprocess.CalledProcessError:
        pass
    shutil.rmtree(db_service.data_dir, ignore_errors=True)
    utils.update_restservice_config({
        'postgresql_host': '127.0.0.1:5432'
    })
    services.RESTSERVICE.restart()
    original_db = database.OriginalDatabase()
    original_db.start(wait_writable=False)
    for ext in ['backup', 'tmp']:
        filename = 'pg_hba.conf.{0}'.format(ext)
        with open(os.path.join(original_db.data_dir, filename), 'w') as f:
            f.write('\n')


def _delete_consul(config):
    consul_service = consul.Consul()
    for service in [watch_handlers.HandlerRunner(), checks.CheckRunner(),
                    consul.ConsulWatcher(), consul.ConsulRecoveryWatcher(),
                    services.IPtablesRestoreService(), consul_service]:
        try:
            service.stop()
            service.disable()
        except subprocess.CalledProcessError:
            pass
    _userdel(config['consul']['user'])
    _groupdel(config['consul']['group'])

    # also remove the cluster group here
    _groupdel(config['group'])
    shutil.rmtree(consul_service.data_dir, ignore_errors=True)
    config_dir = os.path.dirname(consul.CONSUL_CONFIG_PATH)
    for filename in os.listdir(config_dir):
        os.unlink(os.path.join(config_dir, filename))


def _delete_syncthing(config):
    service = syncthing.Syncthing()
    try:
        service.stop()
        service.disable()
    except subprocess.CalledProcessError:
        pass
    _userdel(config['syncthing']['user'])
    _groupdel(config['syncthing']['group'])


def _delete_status():
    os.unlink('/opt/cloudify/.cluster')
    shutil.rmtree('/opt/cloudify/sudo', ignore_errors=True)
    os.unlink('/opt/cloudify/sudo_trampoline.py')


_delete_consul(config)
_delete_syncthing(config)
_delete_database(config)
_delete_status()
