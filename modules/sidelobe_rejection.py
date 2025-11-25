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
from io import StringIO
from configparser import ConfigParser
import numpy as np
import pandas as pd


logging.basicConfig(level=logging.INFO)


def parse_spectra_sofia(bytea):
    """Read sofia output spectra.
    Return arrays for channel, freq, and f_sum across spectra

    """
    print(bytea)
    chan = []
    freq = []
    f_sum = []
    with StringIO(bytea.decode('ascii')) as f:
        for line in f:
            li = line.strip()
            if not li.startswith("#"):
                data = line.split()
                chan.append(int(data[0]))
                freq.append(float(data[1]))
                f_sum.append(float(data[2]))
    spec = pd.Dataframe()
    spec['chan'] = np.array(chan)
    spec['freq'] = np.array(freq)
    spec['f_sum'] = np.array(f_sum)
    return spec


def parse_spectra(bytea):
    """Read extracted spectra """
    chan = []
    freq = []
    vel = []
    f_peak = []
    with StringIO(bytea.decode('ascii')) as f:
        next(f)  # Header
        for line in f:
            data = line.strip().split()
            # Removing NaN values
            if np.isnan(float(data[3])):
                continue
            chan.append(int(data[0]))
            freq.append(float(data[1]))
            vel.append(float(data[2]))
            f_peak.append(float(data[3]))
    spec = pd.DataFrame()
    spec['chan'] = np.array(chan)
    spec['freq'] = np.array(freq)
    spec['vel'] = np.array(vel)
    spec['f_peak'] = np.array(f_peak)
    return spec


def spectra_peak(spectra, n):
    """Find the nth peak value in a spectra data frame. Return f_peak value and channel. """
    f_peak = spectra['f_peak']
    chan = spectra['chan']
    indices = np.argsort(f_peak)[::-1]
    idx = indices[n]
    return f_peak[idx], chan[idx]


async def maser_sidelobe_filter(detections, snr_threshold, second_peak_channels, second_peak_snr):
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
    logging.info('Secondary peak filter using difference %i from 2nd peak with snr = %.2f' % (second_peak_channels, second_peak_snr))
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
            rms = detection_dict['rms']
            spec = detection_dict['spec']

            # If peak channel within 2 pixels of maser peak
            if (abs(peak_z - d_peak_z) < 2):
                # If there is another peak outside of 50 channels from this peak, keep
                f_peak_2, peak_z_2 = spectra_peak(spec, 2)
                if (abs(peak_z_2 - d_peak_z) > second_peak_channels) & ((f_peak_2 / rms) > second_peak_snr):
                    continue

                # Otherwise treat as sidelobe
                sidelobe_d_ids.append(d_id)

        # Add sidelobes to list and remove from unresolved list
        reject_df = pd.concat([reject_df, unresolved_df[unresolved_df['id'].isin(sidelobe_d_ids)]])
        unresolved_df = unresolved_df[~unresolved_df['id'].isin(sidelobe_d_ids)]
        logging.info('Maser %s: matched %i sidelobes. %i remaining unresolved detections' % (name, len(sidelobe_d_ids), len(unresolved_df)))

    assert len(detections) == (len(masers_df) + len(reject_df) + len(unresolved_df)), 'Missing detections...'
    return masers_df, reject_df, unresolved_df


async def main(argv):
    if len(argv) != 1:
        logging.error('sidelobe_rejection.py <config_file>')
        return
    config_file = argv[0]
    assert os.path.exists(config_file), 'Config file does not exist'

    # Database connection
    parser = ConfigParser()
    parser.read(config_file)
    config = parser['SoFiAX']
    run_name = config['run_name']
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
                SELECT d.*, p.spec FROM detection d LEFT JOIN run r ON r.id = d.run_id
                LEFT JOIN product p ON p.detection_id = d.id
                WHERE r.name = $1
            '''
            detections = await conn.fetch(query, run_name)
            detection_dict = [dict(d) for d in detections]
            detections_df = pd.DataFrame(detection_dict)
            detections_df['snr'] = detections_df['f_max'] / detections_df['rms']
            detections_df['spec'] = [parse_spectra(b) for b in detections_df['spec']]
            logging.info('Processing %i detections' % len(detections))

            # Filtering stage 1: SNR > 100 masers
            logging.info('Round 1')
            masers_df, reject_df, unresolved_df = await maser_sidelobe_filter(detections_df, 100, 50, 10)
            logging.info('Accepted: %i, rejected: %i, unresolved: %i\n' % (len(masers_df), len(reject_df), len(unresolved_df)))

            # Filtering stage 2: SNR < 4 reject
            logging.info('Round 2')
            reject_df = pd.concat([reject_df, unresolved_df[unresolved_df['snr'] < 4]])
            unresolved_df = unresolved_df[~(unresolved_df['snr'] < 4)]
            logging.info('SNR filter (round 2): removed %i unresolved detections' % len(unresolved_df[unresolved_df['snr'] < 4]))
            logging.info('Accepted: %i, rejected: %i, unresolved: %i\n' % (len(masers_df), len(reject_df), len(unresolved_df)))

            # Filtering stage 3: SNR > 10 masers
            logging.info('Round 3')
            masers_df_iter2, reject_df_iter2, unresolved_df_iter2 = await maser_sidelobe_filter(unresolved_df, 10, 50, 5)
            masers_df = pd.concat([masers_df, masers_df_iter2])
            reject_df = pd.concat([reject_df, reject_df_iter2])
            unresolved_df = unresolved_df_iter2
            logging.info('Accepted: %i, rejected: %i, unresolved: %i\n' % (len(masers_df), len(reject_df), len(unresolved_df)))

            # Update database
            res = await conn.executemany('UPDATE detection SET accepted=true WHERE id=$1', [[i] for i in masers_df['id']])
            print(res)

    await pool.close()
    logging.info('Closing database connection')
    return


if __name__ == '__main__':
    argv = sys.argv[1:]
    asyncio.run(main(argv))
