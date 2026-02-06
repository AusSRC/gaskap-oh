#!/bin/bash
#SBATCH --time=23:00:00
#SBATCH --mem=32G
#SBATCH --account=ja3
source /software/projects/ja3/ashen/venv/bin/activate
python3 /software/projects/ja3/ashen/gaskap-oh/modules/extract_spectra.py \
    /software/projects/ja3/ashen/gaskap-oh/sofiax.ini