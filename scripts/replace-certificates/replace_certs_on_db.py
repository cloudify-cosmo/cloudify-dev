from __future__ import print_function

import json
import argparse
from datetime import datetime

from manager_rest import config
from manager_rest.flask_utils import setup_flask_app
from manager_rest.storage import models, get_storage_manager  # NOQA


def update_cert(cert_path, name):
    with open(cert_path) as cert_file:
        cert = cert_file.read()
    sm = get_storage_manager()
    try:
        instance = sm.get(models.Certificate,
                          None,
                          filters={'name': name})
    except Exception:
        instance = None

    if instance:
        if instance.value != cert:
            instance.value = cert
            instance.updated_at = datetime.now()
            sm.update(instance)
            print('Replaced cert {0} on DB'.format(name))
            return

    print('CA cert {0} was already replaced'.format(name))


def init_flask_app():
    config.instance.load_configuration()
    setup_flask_app(
        manager_ip=config.instance.postgresql_host,
        hash_salt=config.instance.security_hash_salt,
        secret_key=config.instance.security_secret_key
    )


def main():
    parser = argparse.ArgumentParser(
        description='Replace the CA certificates in the Certificate table')
    parser.add_argument(
        '--input',
        help='Path to a config file containing info needed by this script',
        required=True)

    args = parser.parse_args()
    init_flask_app()

    with open(args.input, 'r') as f:
        script_input = json.load(f)

    update_cert(script_input.get('cert_path'), script_input.get('name'))


if __name__ == '__main__':
    main()
