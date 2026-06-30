#!/usr/bin/env python3

"""A script to extract and write a subcube of a larger FITS cube.
Targeting the following known maser:

    target          ra                dec                Glon      Glat  channel_peak_Flux  brightest_Pixel_RA  brightest_Pixel_DEC
    Target10   16:29:47.33427491 -48:15:51.98488802 335.789009  0.174020        1513               4402                5655

"""

from astropy.io import fits

filename = '/scratch/ja3/jkumar/G335_1665/70731-G335-mainline-May2025/ImageCubes/weights.i.G334_1666_A_1.SB70731.cube_1665.contsub.fits'
subcube_filename = '/scratch/ja3/ashen/gaskap-oh/subcube_weights.fits'

with fits.open(filename) as hdul:
    # Extract the data and header from the original FITS file
    data = hdul[0].data
    header = hdul[0].header

    # Define the subcube region (example: a 100x100x100 cube starting at (50, 50, 50))
    x_start, x_end = 4000, 5000
    y_start, y_end = 5000, 6000
    z_start, z_end = 0, 3841

    # Extract the subcube
    subcube_data = data[z_start:z_end, :, y_start:y_end, x_start:x_end]

    # Update the header for the subcube (optional)
    header['NAXIS1'] = x_end - x_start
    header['NAXIS2'] = y_end - y_start
    header['NAXIS4'] = z_end - z_start
    header['CRPIX1'] -= x_start
    header['CRPIX2'] -= y_start
    header['CRPIX4'] -= z_start

    # Write the subcube to a new FITS file
    fits.writeto(subcube_filename, subcube_data, header, overwrite=True)
    print(f'Subcube extracted and saved to {subcube_filename}')