#!/usr/bin/env python
"""A script to add Cloudify Stage to an existing snapshot.

To add Cloudify Stage data (config, templates and widgets) to an existing
snapshot, first create a snapshot as usual (eg. using the CLI), then run
this script passing the name of that snapshot as an argument. The Cloudify
Stage data will be added to that snapshot, allowing you to download it as
normal and restore it on a 4.1 (or newer) Cloudify Manager.

Steps to use:
    1. cfy snapshot create snap1
    2. [on the manager] python this_script.py snap1
    3. cfy snapshot download snap1
"""


import os
import logging
import argparse
import zipfile

SNAPSHOTS_BASE_DIR = '/opt/manager/resources/snapshots'
STAGE_BASE_DIR = '/opt/cloudify-stage'
STAGE_DIRS = [
    'conf',
    'dist/templates',
    'dist/widgets'
]
# name of the directory inside the snapshot that stores stage data
STAGE_SNAPSHOT_PREFIX = 'stage'


def _setup_logging(args):
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)s: %(message)s')


def _parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('snapshot_name')
    parser.add_argument('--stage-base-dir',
                        dest='stage_base_dir',
                        default=STAGE_BASE_DIR)
    return parser.parse_args()


def _add_stage_to_snapshot(args):
    logging.debug('Looking for snapshot %s', args.snapshot_name)
    snapshot_path = os.path.join(SNAPSHOTS_BASE_DIR,
                                 args.snapshot_name,
                                 '{0}.zip'.format(args.snapshot_name))
    if os.path.exists(snapshot_path):
        logging.info('Found snapshot: %s', args.snapshot_name)
    else:
        raise ValueError('Snapshot {0} not found!'.format(args.snapshot_name))

    logging.info('Adding stage directories to the snapshot')
    _add_stage_directories_to_zipfile(snapshot_path, STAGE_DIRS)
    logging.info('Stage directories to were added to the snapshot')


def _add_stage_directories_to_zipfile(zip_filename, dirs):
    """Adds the passed directories to the zip file at zip_filename.

    The directories will be added under the STAGE_SNAPSHOT_PREFIX
    subdirectory.
    Note that this function is based on
    cloudify_system_workflows.snapshots.utils.make_zip64_archive
    """
    zip_context_manager = zipfile.ZipFile(
        zip_filename,
        'a',
        compression=zipfile.ZIP_DEFLATED,
        allowZip64=True,
    )

    with zip_context_manager as zip_file:
        for directory in dirs:
            full_path = os.path.join(STAGE_BASE_DIR, directory)
            logging.debug('Adding %s', full_path)
            path = os.path.normpath(full_path)
            base_dir = path

            for dirpath, dirnames, filenames in os.walk(full_path):
                for dirname in sorted(dirnames):
                    path = os.path.normpath(os.path.join(dirpath, dirname))
                    logging.debug('Copying %s', path)
                    zip_file.write(
                        path,
                        os.path.join('stage', os.path.relpath(path, base_dir)))

                for filename in filenames:
                    path = os.path.normpath(os.path.join(dirpath, filename))
                    if os.path.isfile(path):
                        logging.debug('Copying %s', path)
                        zip_file.write(
                            path,
                            os.path.join('stage',
                                         os.path.relpath(path, base_dir)))


if __name__ == '__main__':
    args = _parse_args()
    _setup_logging(args)
    _add_stage_to_snapshot(args)
