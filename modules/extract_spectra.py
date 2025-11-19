#!/usr/bin/env python

"""
Extract full spectra for all sofia detections at the position of the peak pixel.
Get detection information from output xml catalog.

Usage:
    python extract_spectra.py <output_dir>

"""

import os
import time
import sys
import glob
import asyncio
import logging
import numpy as np
import pandas as pd
from astropy.io import fits
from astropy.io.votable import parse


logging.basicConfig(level=logging.INFO)


async def extract_spec(data, df, x, y, filename):
    """Extract the spectra from hdul. Calculate velocity. Construct dataframe
    Write dataframe file.

    """
    start = time.time()
    flux = data[:, 0, y, x]
    df['Brightness'] = flux
    df.to_csv(filename, sep=' ', index=False, float_format="%.6f", header=True)
    format_output = df.to_string(index=False, col_space=4, justify='left')
    with open(filename, 'w') as f:
        f.write(format_output)
    logging.info('(%.2f s) Extract spectra and write file %s' % (time.time() - start, filename))
    return


async def main(argv):
    basedir = argv[0]
    assert os.path.exists(basedir), 'Directory does not exist'
    catalogs = glob.glob(os.path.join(basedir, '*_cat.xml'))

    # Get image cube file (should be the same)
    ref_cat = catalogs[0]
    votable = parse(ref_cat)
    params = votable.resources[0].params
    ref_input_data = list(filter(lambda p: p.ID == 'input.data', params))[0].value
    assert os.path.exists(ref_input_data), 'Image file does not exist'
    logging.info('Input data file: %s' % ref_input_data)

    # Memory map open fits file
    with fits.open(ref_input_data, memmap=True, mode='denywrite') as hdul:
        header = hdul[0].header
        data = hdul[0].data

        # Get velocities
        freq_start = header['CRVAL4']
        freq_step = header['CDELT4']
        freq_rest = header['RESTFRQ']
        nchan = int(header['CRPIX4'])
        freq = freq_start + np.arange(nchan) * freq_step
        c = 299792458  # m/s
        vel = (c * (freq_rest - freq) / freq) / 1000

        # Create dataframe template
        df = pd.DataFrame({
            'Chan': np.arange(len(freq)),
            'Frequency (Hz)': freq,
            'Velocity (km/s)': vel
        })

        for c in catalogs:
            logging.info('Updating spectra in detection from %s' % c)
            tasks = []
            start = time.time()

            votable = parse(c)
            params = votable.resources[0].params
            input_region = eval(list(filter(lambda p: p.ID == 'input.region', params))[0].value)
            x_ref, _, y_ref, _, _, _ = input_region
            input_data = list(filter(lambda p: p.ID == 'input.data', params))[0].value
            if input_data != ref_input_data:
                logging.info('Catalog has different input data %s. Skipping' % input_data)
                continue
            output_filename = list(filter(lambda p: p.ID == 'output.filename', params))[0].value
            table = votable.get_first_table().to_table()

            for row in table:
                detection_id = row['id']
                detection_name = row['name']
                x = int(row['x_peak']) + x_ref
                y = int(row['y_peak']) + y_ref

                spec_file = os.path.join(basedir, f'{output_filename}_cubelets', f'{output_filename}_{detection_id}_spec.txt')
                if not os.path.exists(spec_file):
                    logging.warning('Spectrum file missing. Creating new one.')
                logging.info(f'Updating detection {detection_name} spectra file {spec_file}')
                task = asyncio.create_task(extract_spec(data, df, x, y, spec_file))
                tasks.append(task)

        await asyncio.gather(*tasks)
        logging.info('Complete.')
    return


if __name__ == '__main__':
    argv = sys.argv[1:]
    asyncio.run(main(argv))
