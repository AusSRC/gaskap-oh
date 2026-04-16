#!/bin/bash
#SBATCH --account=ja3
#SBATCH --time=1:00:00
#SBATCH --mem=32G
SOFTWARE_DIR=/software/projects/ja3/ashen
source $SOFTWARE_DIR/venv/bin/activate
python $SOFTWARE_DIR/gaskap-oh/modules/reset_run.py \
    $SOFTWARE_DIR/gaskap-oh/config/sofiax.ini
