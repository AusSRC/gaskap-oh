#!/bin/bash
#SBATCH --time=23:00:00
#SBATCH --mem=32G
#SBATCH --account=ja3
SOFTWARE_DIR=/software/projects/ja3/ashen
source $SOFTWARE_DIR/venv/bin/activate
python3 $SOFTWARE_DIR/gaskap-oh/modules/extract_spectra.py \
    $SOFTWARE_DIR/gaskap-oh/sofiax.ini