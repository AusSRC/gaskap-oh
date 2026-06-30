#!/usr/bin/env python3

"""
Generate summary figures for GASKAP-OH detections using Plotly.
Create .html files alongside the output cubelet files for direct ingestion with SoFiAX
"""

import os
import sys
import gzip
import glob
import numpy as np
import pandas as pd
from astropy.io.votable import parse, parse_single_table
from astropy.io import fits
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def interactive_plot(output_file, name, mom0, spec_df):
    """Generate plotly figure with subplots for detection following
    GASKAP-OH requirements. Can be updated. Save as html file alongside
    output cubelet file.

    """
    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.5, 0.5],
        specs=[[{"type": "xy"}, {"type": "xy"}]],
        subplot_titles=("Moment 0", "2D peak spectrum")
    )
    # Plot moment 0 map
    fig.add_trace(
        go.Heatmap(z=mom0.astype(float), colorscale='Viridis', name='Moment 0 Map'),
        row=1, col=1
    )
    fig.update_xaxes(title_text="X pixel", row=1, col=1)
    fig.update_yaxes(title_text="Y pixel", row=1, col=1)

    # Plot spectra
    fig.add_trace(
        go.Scatter(x=spec_df['chan'], y=spec_df['f_peak [Jy]'], ids=['Chan', 'F_peak [Jy]'], mode='lines+text', name='Spectrum'),
        row=1, col=2
    )
    fig.update_xaxes(title_text="Channel", row=1, col=2)
    fig.update_yaxes(title_text="Flux Density [Jy]", row=1, col=2)

    fig.update_layout(title=name, height=600, width=1000)
    fig.write_html(output_file)


def parse_spec_aperture(filename):
    """Parse the SoFiA generated spec_aperture.txt file to extract
    a Python data frame

    """
    data = np.loadtxt(filename)
    df = pd.DataFrame(data, columns=['chan', 'freq [Hz]', 'f_sum [Jy]', 'n_pix', 'f_peak [Jy]'])
    return df


def main(argv):
    products_dir = argv[0]
    if not os.path.exists(products_dir):
        raise FileNotFoundError(f"Products directory {products_dir} does not exist.")

    # products_dir = '/scratch/ja3/ashen/gaskap-oh/gaskap-oh-test-2026-06-23/products/'
    files = glob.glob(os.path.join(products_dir, '*_cat.xml'))
    print(f"Found {len(files)} catalog files in {products_dir}")
    instances = [os.path.splitext(os.path.basename(f))[0].replace('_cat', '') for f in files]

    for instance in instances:
        catalog_file = os.path.join(products_dir, f'{instance}_cat.xml')
        cubelets_dir = os.path.join(products_dir, f'{instance}_cubelets')
        assert os.path.isdir(cubelets_dir), f"Directory {cubelets_dir} does not exist."
        assert os.path.isfile(catalog_file), f"Catalog file {catalog_file} does not exist."

        # Read catalog for detection names and metadata
        vot = parse(catalog_file)
        for resource in vot.resources:
            for param in resource.params:
                pass

        # get votable as astropy table
        votable = parse_single_table(catalog_file)
        n_cubelets = len(votable.array)
        detection_table = votable.to_table()
        print(f"Number of detections in catalog: {n_cubelets}")

        # Fetch all products
        for row in detection_table:
            name = row['name']
            mom0_file = os.path.join(cubelets_dir, f"{instance}_{row['id']}_mom0.fits")
            aper_spec_file = os.path.join(cubelets_dir, f"{instance}_{row['id']}_spec_aperture.txt")
            output_html = os.path.join(cubelets_dir, f"{instance}_{row['id']}_summary.html")
            output_html_gz = os.path.join(cubelets_dir, f"{instance}_{row['id']}_summary.html.gz")

            # Generate plots
            print(f"Processing detection {name} (ID: {row['id']})")
            spec_df = parse_spec_aperture(aper_spec_file)
            with fits.open(mom0_file) as hdu_mom0:
                mom0_data = hdu_mom0[0].data
            interactive_plot(output_html, name, mom0_data, spec_df)

            # Compress
            with open(output_html, 'rb') as f:
                with gzip.open(output_html_gz, 'wb') as f_gz:
                    f_gz.writelines(f)


if __name__ == "__main__":
    main(sys.argv[1:])