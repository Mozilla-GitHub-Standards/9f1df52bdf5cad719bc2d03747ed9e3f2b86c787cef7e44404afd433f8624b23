"""
funsize.backend.core
~~~~~~~~~~~~~~~~~~

This module contains the brain of the entire funsize project

"""

import errno
import logging
import os
import subprocess
import tempfile

import funsize.utils.fetch as fetch
import funsize.cache.cache as cache
import funsize.utils.oddity as oddity

TOOLS_DIR = "/perma/tools"  # TODO: pass or keep them under the tree?


def get_complete_mar(url, mar_hash, output_file):
    """ Return binary string if no output_file specified """
    logging.info('Downloading complete MAR %s with mar_hash %s', url, mar_hash)

    cacheo = cache.Cache()
    if url.startswith('http://') or url.startswith('https://'):
        fetch.downloadmar(url, mar_hash, output_file)
        cacheo.save(output_file, mar_hash, 'complete', isfilename=True)
    else:
        cacheo.retrieve(mar_hash, 'complete', output_file=output_file)

    logging.info('Satisfied request for complete MAR %s with mar_hash %s',
                 url, mar_hash)


def build_partial_mar(new_cmar_url, new_cmar_hash, old_cmar_url, old_cmar_hash,
                      identifier, channel_id, product_version):
    """ Function that returns the partial MAR file to transition from the mar
        given by old_cmar_url to new_cmar_url
    """
    logging.info('Creating temporary working directories')
    TMP_MAR_STORAGE = tempfile.mkdtemp(prefix='cmar_storage_')
    logging.debug('MAR storage: %s', TMP_MAR_STORAGE)
    TMP_WORKING_DIR = tempfile.mkdtemp(prefix='working_dir_')
    logging.debug('Working dir storage: %s', TMP_WORKING_DIR)

    new_cmar_path = os.path.join(TMP_MAR_STORAGE, 'new.mar')
    old_cmar_path = os.path.join(TMP_MAR_STORAGE, 'old.mar')

    logging.info('Looking up the complete MARs required')
    get_complete_mar(new_cmar_url, new_cmar_hash, new_cmar_path)
    get_complete_mar(old_cmar_url, old_cmar_hash, old_cmar_path)

    logging.info('Creating cache connections')
    cacheo = cache.Cache()
    try:
        local_pmar_location = generate_partial_mar(new_cmar_path, old_cmar_path,
                                                   TOOLS_DIR,
                                                   channel_id,
                                                   product_version,
                                                   working_dir=TMP_WORKING_DIR)
        logging.debug('Partial MAR generated at %s', local_pmar_location)
    except oddity.ToolError:
        cacheo.delete_from_cache(identifier, 'partial')
        raise

    logging.info('Saving PMAR %s to cache with key %s',
                 local_pmar_location, identifier)
    cacheo.save(local_pmar_location, identifier, 'partial', isfilename=True)


def generate_partial_mar(cmar_new, cmar_old, difftools_path, channel_id,
                         product_version, working_dir=None):
    """ cmar_new is the path of the newer complete .mar file
        cmar_old is the path of the older complete .mar file
        difftools_path specifies the path of the directory in which
        the difftools, including mar,mbsdiff exist
    """
    if not working_dir:
        working_dir = '.'

    UNWRAP = os.path.join(difftools_path, 'unwrap_full_update.pl')
    MAKE_INCREMENTAL = os.path.join(difftools_path,
                                    'make_incremental_update.sh')
    MAR = os.path.join(difftools_path, 'mar')
    MBSDIFF = os.path.join(difftools_path, 'mbsdiff')

    my_env = os.environ.copy()
    my_env['MAR'] = MAR
    my_env['MBSDIFF'] = MBSDIFF
    my_env['MOZ_CHANNEL_ID'] = channel_id
    my_env['MOZ_PRODUCT_VERSION'] = product_version
    my_env['LC_ALL'] = 'C'

    try:
        os.mkdir(working_dir)
    except Exception as e:
        if e.errno == errno.EEXIST and os.path.isdir(working_dir):
            pass
        else:
            raise oddity.ToolError('Error while initiating working dir')

    cmn_name = os.path.basename(cmar_new)
    cmn_wd = os.path.join(working_dir, cmn_name)

    try:
        os.mkdir(cmn_wd)
    except Exception as e:
        if e.errno == errno.EEXIST and os.path.isdir(cmn_wd):
            pass
        else:
            raise oddity.ToolError('Error making working dir while unwrapping')

    logging.info('Unwrapping MAR#1')
    logging.debug('subprocess call to %s',
                  str(([UNWRAP, cmar_new], 'cwd:', cmn_wd, 'env:', my_env)))

    subprocess.call([UNWRAP, cmar_new], cwd=cmn_wd, env=my_env)

    cmo_name = os.path.basename(cmar_old)
    cmo_wd = os.path.join(working_dir, cmo_name)

    try:
        os.mkdir(cmo_wd)
    except Exception as e:
        if e.errno == errno.EEXIST and os.path.isdir(cmo_wd):
            pass
        else:
            raise oddity.ToolError('Error while initiating working dir')

    logging.info('Unwrapping MAR#2')
    logging.debug('subprocess call to %s',
                  str(([UNWRAP, cmar_old], 'cwd:', cmo_wd, 'env:', my_env)))

    subprocess.call([UNWRAP, cmar_old], cwd=cmo_wd, env=my_env)

    pmar_name = '-'.join([cmo_name, cmn_name])
    pmar_path = os.path.join(working_dir, pmar_name)

    logging.info('Generating partial mar @ %s', pmar_path)
    logging.debug('subprocess call to %s',
                  str(([MAKE_INCREMENTAL, pmar_path, cmo_wd, cmn_wd],
                       'cwd=', working_dir, 'env=', my_env)))

    subprocess.call(["bash", MAKE_INCREMENTAL, pmar_path, cmo_wd, cmn_wd],
                    cwd=working_dir, env=my_env)
    logging.info('Partial now available at path: %s', pmar_path)

    return pmar_path
