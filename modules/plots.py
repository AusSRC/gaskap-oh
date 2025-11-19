#!/usr/bin/env python3

"""
Adding summary figures for GASKAP-OH detections.
Uses SoFiAX config file to establish database connection and run.
"""

import os
import sys
import asyncio
import asyncpg
import logging
from io import StringIO
import pandas as pd
import numpy as np
from configparser import ConfigParser
import matplotlib.pyplot as plt


logging.basicConfig(level=logging.INFO)


def freq_to_vel(freq_array, restfreq):
    """Radio velocities. Using Hz and m/s"""
    C = 299792458  # m/s
    vel_array = (restfreq - freq_array) * C / restfreq
    return vel_array


def parse_spectra_sofia(bytea):
    """Read sofia output spectra.
    Return arrays for channel, freq, and f_sum across spectra

    """
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

    if not chan or not freq or not f_sum:
        logging.info('Spec file empty')
        return None

    chan = np.array(chan)
    freq = np.array(freq)
    f_sum = np.array(f_sum)
    return chan, freq, f_sum


async def main(argv):
    # Read config
    config_file = argv[0]
    assert os.path.exists(config_file), 'Config file does not exist'
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

    # Constants
    restfreq = 1665401800.0

    # Database connection
    pool = await asyncpg.create_pool(**creds, server_settings={'search_path': schema})
    async with pool.acquire() as conn:
        async with conn.transaction():
            run = await conn.fetchrow('SELECT * FROM run WHERE name=$1', run_name)
            logging.info('Running sidelobe rejection for detections in run %s' % run['name'])
            assert run is not None, 'Run does not exist'

            query = '''
                SELECT d.*, p.spec FROM detection d
                LEFT JOIN run r ON r.id = d.run_id
                LEFT JOIN product p ON p.detection_id = d.id
                WHERE r.name = $1
            '''
            detections = await conn.fetch(query, run_name)
            detection_dict = [dict(d) for d in detections]
            detections_df = pd.DataFrame(detection_dict)

            # Create plot
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6), sharex=True)
            cmap = plt.cm.get_cmap('nipy_spectral', len(detections))
            ax1.grid(True)
            ax2.grid(True)
            ax1.set_xlabel('Velocity (km/s)')
            ax2.set_xlabel('Velocity (km/s)')
            ax1.set_ylabel('Flux (Jy)')
            ax1.set_title('GASKAP-OH detection spectra')

            logging.info('Processing %i detections' % len(detections))
            for idx, detection in detections_df.iterrows():
                logging.info('[%i/%i] %s' % (idx+1, len(detections), detection['name']))
                spec_bytes = detection['spec']
                _, freq_array, f_sum_array = parse_spectra_sofia(spec_bytes)
                vel_array = freq_to_vel(freq_array, restfreq) / 1e3  # km/s
                ax1.plot(vel_array, f_sum_array, color=cmap(idx), linewidth=1)

            # Save plot
            fig.tight_layout()
            plt.savefig('spectra.png')
            plt.close()
    return


if __name__ == '__main__':
    argv = sys.argv[1:]
    asyncio.run(main(argv))
