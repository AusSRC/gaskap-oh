#!/usr/bin/env python

"""
Extract full spectra for all sofia detections at the position of the peak pixel.
Write spectra to file system as csv file.
Get detection information from output xml catalog.

Usage:
    python extract_spectra.py <output_dir>

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
from astropy.io.votable import parse, parse_single_table


logging.basicConfig(level=logging.INFO)


async def get_file_bytes(path: str, mode: str = "rb"):
    buffer = []
    if not os.path.isfile(path):
        return b""
    async with aiofiles.open(path, mode) as f:
        while True:
            buff = await f.read()
            if not buff:
                break
            buffer.append(buff)
        if "b" in mode:
            return b"".join(buffer)
        else:
            return "".join(buffer)


async def extract_spec(data, x, y, filename, write=False):
    """Extract spectra from the data for an x, y position.
    Write to a temporary file. Makes an assumption on the shape of the data.

    """
    start = time.time()

    # Extract spectra
    df = pd.DataFrame()
    flux = data[:, 0, y, x]
    df["Chan"] = np.arange(len(flux))
    df["Brightness"] = flux
    if write:
        df.to_csv(filename, sep=" ", index=False, float_format="%.6f", header=True)
    logging.info("Extracted spectra for detection at position (%i, %i) in %.2f s" % (x, y, time.time() - start))
    return


async def main(argv):
    """Run program with local output

    """
    start = time.time()
    output_dir = argv[0]
    assert os.path.exists(output_dir), "Output directory does not exist"
    logging.info("Extracting spectra for detections in output directory %s" % output_dir)
    catalog_file = os.path.join(output_dir, "output_cat.xml")

    # Parse VOTable to get input data file
    input_data_file = None
    votable = parse(catalog_file)
    for resource in votable.resources:
        for param in resource.params:
            if param.ID == "input.data":
                input_data_file = param.value
                break
        if not input_data_file:
            raise ValueError("input.data parameter not found in VOTable")

    # Iterate over catalog
    catalog = parse_single_table(catalog_file)
    table = catalog.to_table()

    # Open image
    with fits.open(input_data_file, memmap=True, mode="denywrite") as hdul:
        data = hdul[0].data

        # Iterate through detections and extract spectra
        for row in table:
            id = row["id"]
            x_peak, y_peak = row["x_peak"], row["y_peak"]
            filename = os.path.join(output_dir, 'output_cubelets', f"output_{id}_spec.csv")
            logging.info("Processing detection %i at position (%i, %i)", id, x_peak, y_peak)
            await extract_spec(data, x_peak, y_peak, filename, write=True)

    logging.info("Program complete in %.2f s" % (time.time() - start))
    return


if __name__ == "__main__":
    argv = sys.argv[1:]
    asyncio.run(main(argv))
