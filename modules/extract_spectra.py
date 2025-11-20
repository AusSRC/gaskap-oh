#!/usr/bin/env python

"""
Extract full spectra for all sofia detections at the position of the peak pixel.
Write temporary files to /tmp
Get detection information from output xml catalog.

Usage:
    python extract_spectra.py <sofiax.ini>

"""

import os
import time
import sys
import glob
import asyncio
import asyncpg
import aiofiles
import logging
import numpy as np
import pandas as pd
from configparser import ConfigParser
from astropy.io import fits
from astropy.io.votable import parse


logging.basicConfig(level=logging.INFO)


async def get_file_bytes(path: str, mode: str = 'rb'):
    buffer = []
    if not os.path.isfile(path):
        return b''
    async with aiofiles.open(path, mode) as f:
        while True:
            buff = await f.read()
            if not buff:
                break
            buffer.append(buff)
        if 'b' in mode:
            return b''.join(buffer)
        else:
            return ''.join(buffer)


async def extract_spec(detection_id, data, df, x, y, conn):
    """Extract the spectra from hdul. Convert to string, then bytes.
    Update detection product in database.

    """
    start = time.time()

    # Extract spectra
    flux = data[:, 0, y, x]
    df['Brightness'] = flux
    assert len(flux) == len(df['Frequency (Hz)']), 'Number of channels is not the same'
    df.to_csv(sep=' ', index=False, float_format="%.6f", header=True)
    df_string = df.to_string(index=False, col_space=4, justify='left')
    bytea = bytes(df_string, 'utf-8')

    # Update database
    query = 'UPDATE product SET spec=$1 WHERE detection_id=$2'
    res = await conn.execute(query, bytea, detection_id)
    logging.debug(res)

    logging.info('(%.2f s) Updated spec product for detection %i' % (time.time() - start, detection_id))
    return


async def main(argv):
    start = time.time()
    config_file = argv[0]
    assert os.path.exists(config_file), 'Config file does not exist'
    parser = ConfigParser()
    parser.read(config_file)
    config = parser['SoFiAX']
    creds = {
        "host": config['db_hostname'],
        "database": config['db_name'],
        "user": config['db_username'],
        "password": config['db_password'],
	    "port": config['db_port']
    }
    schema = config['db_schema']
    run_name = config['run_name']
    logging.info('Extracting spectra for detections in run %s' % run_name)

    # With database connection
    pool = await asyncpg.create_pool(**creds, server_settings={'search_path': schema})
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Get instance (and image cube file)
            run = await conn.fetchrow('SELECT * FROM run WHERE name=$1', run_name)
            logging.info('Running sidelobe rejection for detections in run %s' % run['name'])
            assert run is not None, 'Run does not exist'
            instance = await conn.fetchrow('SELECT * FROM instance WHERE run_id = $1 LIMIT 1', run['id'])
            assert instance is not None, 'Instance does not exist'
            instance = dict(instance)
            params = eval(instance['parameters'])
            image_cube_file = params['input.data']
            assert os.path.exists(image_cube_file), 'Image cube %s does not exist' % image_cube_file
            logging.info('Extracting spectra from image cube %s' % image_cube_file)

            # Fetch all detections in run
            query = '''
                SELECT d.*, i.parameters FROM detection d LEFT JOIN run r ON r.id = d.run_id
                LEFT JOIN instance i ON d.instance_id = i.id
                WHERE r.name=$1
            '''
            detections = await conn.fetch(query, run_name)
            detection_dict = [dict(d) for d in detections]
            detections_df = pd.DataFrame(detection_dict)
            detections_df['parameters'] = [eval(p) for p in detections_df['parameters']]
            logging.info('Updating spectra for %i detections', len(detections_df))

            # Memory map open fits file
            with fits.open(image_cube_file, memmap=True, mode='denywrite') as hdul:
                header = hdul[0].header
                data = hdul[0].data
                tasks = []

                # Get velocities
                freq_start = header['CRVAL4']
                freq_step = header['CDELT4']
                freq_rest = header['RESTFRQ']
                nchan = int(header['NAXIS4'])
                freq = freq_start + np.arange(nchan) * freq_step
                c = 299792458  # m/s
                vel = (c * (freq_rest - freq) / freq) / 1000

                # Create dataframe template
                df = pd.DataFrame({
                    'Chan': np.arange(len(freq)),
                    'Frequency (Hz)': freq,
                    'Velocity (km/s)': vel
                })

                # Extract and update for all detections
                for idx, d in detections_df.iterrows():
                    name = d['name']
                    detection_id = int(d['id'])
                    region = eval(d['parameters']['input.region'])
                    x_ref, _, y_ref, _, _, _ = region
                    x = int(d['x_peak']) + x_ref
                    y = int(d['y_peak']) + y_ref
                    await extract_spec(detection_id, data, df, x, y, conn)

    await pool.close()
    logging.info('Program complete in %.2f s' % (time.time() - start))
    return


if __name__ == '__main__':
    argv = sys.argv[1:]
    asyncio.run(main(argv))
