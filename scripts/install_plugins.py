
from tempfile import mkdtemp
from os.path import join, exists
from argparse import ArgumentParser
from shutil import copytree, rmtree
from platform import linux_distribution

from wagon.utils import get_platform
from cloudify_rest_client.client import CloudifyClient


def _plugin_to_str(plugin):
    return '<package: `{0}`, version: `{1}`, tenant: `{2}`>'.format(
        plugin['package_name'],
        plugin['package_version'],
        plugin['tenant_name'])


def _create_client(password, tenant):
    return CloudifyClient(
        host='127.0.0.1', username='admin', password=password, tenant=tenant)


def _get_plugins(password):
    client = _create_client(password, 'default_tenant')
    response = client.plugins.list(_all_tenants=True)
    return response


def _copy_plugins_files():
    source = '/opt/manager/resources/plugins'
    target = join(mkdtemp(), 'plugins')
    copytree(source, target)
    return target


def _plugin_installable_on_current_platform(plugin):
    if not get_platform:
        return True
    dist, _, release = linux_distribution(full_distribution_name=False)
    dist, release = dist.lower(), release.lower()
    return (plugin['supported_platform'] == 'any' or all([
        plugin['supported_platform'] == get_platform(),
        plugin['distribution'] == dist,
        plugin['distribution_release'] == release
    ]))


def _filter_plugins(plugins, plugins_dir):
    result = []
    for plugin in plugins:
        plugin_str = _plugin_to_str(plugin)
        plugin_dir = join(plugins_dir, plugin['id'])
        plugin_install_path = join('/opt/mgmtworker/env/plugins',
                                   plugin['tenant_name'],
                                   '{0}-{1}'.format(plugin['package_name'],
                                                    plugin['package_version']))
        if exists(plugin_install_path):
            print 'plugin already installed: {0}'.format(plugin_str)
        elif not exists(plugin_dir):
            print 'no wagon was found for plugin: {0}'.format(plugin_str)
        elif not _plugin_installable_on_current_platform(plugin):
            print 'plugin not installable on this platform: {0}'.format(
                plugin_str)
        else:
            result.append(plugin)
    if result:
        print 'plugins to install:'
    for plugin in result:
        print _plugin_to_str(plugin)
    return result


def _upload_plugins(plugins, plugins_dir, password):
    for plugin in plugins:
        client = _create_client(password, plugin['tenant_name'])
        print 'Deleting plugin: {0}'.format(_plugin_to_str(plugin))
        client.plugins.delete(plugin['id'], force=True)
        print 'Uploading plugin: {0}'.format(_plugin_to_str(plugin))
        client.plugins.upload(
            join(plugins_dir, plugin['id'], plugin['archive_name']))


def _parse_password():
    parser = ArgumentParser(description='install plugins on a cloudify '
                                        'manager after snapshot restore')
    parser.add_argument('password', help='bootstrap admin password')
    return vars(parser.parse_args())['password']


def main():
    print 'Parsing password...'
    password = _parse_password()
    print 'Listing plugins...'
    all_plugins = _get_plugins(password)
    print 'Copying plugins archives...'
    plugins_dir = _copy_plugins_files()
    print 'Filtering plugins to install...'
    plugins_to_install = _filter_plugins(all_plugins, plugins_dir)
    print 'Deleting and uploading again plugins that need to be installed...'
    _upload_plugins(plugins_to_install, plugins_dir, password)
    print 'Removing plugins archives...'
    rmtree(plugins_dir)
    if plugins_to_install:
        print 'Successfully installed all plugins!'
    else:
        print 'No plugins that needs installation found!'


if __name__ == '__main__':
    main()
