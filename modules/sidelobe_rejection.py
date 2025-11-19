#!/usr/bin/env python3

"""
Implementing Jay's sidelobe rejection strategy for the GASKAP-OH project
Updating source finding database in place.
"""

import os
import sys
import logging
import asyncio
import asyncpg
from configparser import ConfigParser
import pandas as pd


logging.basicConfig(level=logging.INFO)


async def maser_sidelobe_filter(detections, snr_threshold):
    """Used as part of the sidelobe rejection workflow:

    1. Assume detections are masers if they have SNR > snr_threshold argument
       (set accepted = true)
    2. Assume probable sidelobe if detection peak channel is the same (within 2 channels)
       of an accepted maser
       (set rejected = true)
    3. remaining unresolved detections are returned

    Arguments:
        - detections:       List of detection objects (DataFrame)
        - snr_threshold:    Signal-noise threshold for assuming a detection
                            is a maser (Integer)

    Returns:
        - maser_df:         Table of masers
        - reject_df:        Table of sidelobes
        - unresolved_df:    Table of unresolved detections

    """
    logging.info('Maser-sidelobe filter iteration with snr threshold = %i' % snr_threshold)
    masers_df = detections[detections['snr'] >= snr_threshold]
    unresolved_df = detections[detections['snr'] < snr_threshold]
    logging.info('Number of assumed masers: %i' % len(masers_df))

    reject_df = pd.DataFrame()

    # Identify sidelobes
    for idx, maser in masers_df.iterrows():
        maser_dict = dict(maser)
        logging.debug(maser_dict)
        peak_z = maser_dict['z_peak']
        name = maser_dict['name']
        sidelobe_d_ids = []

        for _, detection in unresolved_df.iterrows():
            detection_dict = dict(detection)
            d_id = detection_dict['id']
            d_peak_z = detection_dict['z_peak']

            # If peak channel within 2 pixels of maser peak, consider as sidelobe
            if (abs(peak_z - d_peak_z) < 2):
                sidelobe_d_ids.append(d_id)

        # Add sidelobes to list and remove from unresolved list
        reject_df = pd.concat([reject_df, unresolved_df[unresolved_df['id'].isin(sidelobe_d_ids)]])
        unresolved_df = unresolved_df[~unresolved_df['id'].isin(sidelobe_d_ids)]
        logging.info('Maser %s: matched %i sidelobes. %i remaining unresolved detections' % (name, len(sidelobe_d_ids), len(unresolved_df)))

    assert len(detections) == (len(masers_df) + len(reject_df) + len(unresolved_df)), 'Missing detections...'
    return masers_df, reject_df, unresolved_df


async def parse_spectra(bytes):
    """Read byte array spectra file and return as dataframe.

    """
    return


async def main(argv):
    if len(argv) != 2:
        logging.error('sidelobe_rejection.py <config_file> <run_name>')
        return
    config_file = argv[0]
    run_name = argv[1]
    assert os.path.exists(config_file), 'Config file does not exist'

    # Database connection
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
    pool = await asyncpg.create_pool(**creds, server_settings={'search_path': schema})
    async with pool.acquire() as conn:
        async with conn.transaction():
            run = await conn.fetchrow('SELECT * FROM run WHERE name=$1', run_name)
            logging.info('Running sidelobe rejection for detections in run %s' % run['name'])
            assert run is not None, 'Run does not exist'

            query = '''
                SELECT d.* FROM detection d LEFT JOIN run r ON r.id = d.run_id
                WHERE r.name = $1
            '''
            detections = await conn.fetch(query, run_name)
            detection_dict = [dict(d) for d in detections]
            detections_df = pd.DataFrame(detection_dict)
            detections_df['snr'] = detections_df['f_max'] / detections_df['rms']
            logging.info('Processing %i detections' % len(detections))

            # Filtering stage 1: SNR > 100 masers
            logging.info('Round 1')
            masers_df, reject_df, unresolved_df = await maser_sidelobe_filter(detections_df, 100)
            logging.info('Accepted: %i, rejected: %i, unresolved: %i\n' % (len(masers_df), len(reject_df), len(unresolved_df)))

            # Filtering stage 2: SNR < 4 reject
            logging.info('Round 2')
            reject_df = pd.concat([reject_df, unresolved_df[unresolved_df['snr'] < 4]])
            unresolved_df = unresolved_df[~(unresolved_df['snr'] < 4)]
            logging.info('SNR filter (round 2): removed %i unresolved detections' % len(unresolved_df[unresolved_df['snr'] < 4]))
            logging.info('Accepted: %i, rejected: %i, unresolved: %i\n' % (len(masers_df), len(reject_df), len(unresolved_df)))

            # Filtering stage 3: SNR > 10 masers
            logging.info('Round 3')
            masers_df_iter2, reject_df_iter2, unresolved_df_iter2 = await maser_sidelobe_filter(unresolved_df, 10)
            masers_df = pd.concat([masers_df, masers_df_iter2])
            reject_df = pd.concat([reject_df, reject_df_iter2])
            unresolved_df = unresolved_df_iter2
            logging.info('Accepted: %i, rejected: %i, unresolved: %i\n' % (len(masers_df), len(reject_df), len(unresolved_df)))

            # Update database

    await pool.close()
    logging.info('Closing database connection')
    return


if __name__ == '__main__':
    argv = sys.argv[1:]
    asyncio.run(main(argv))
