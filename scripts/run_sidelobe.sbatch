#!/bin/bash
#SBATCH --account=ja3
#SBATCH --time=18:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
source /software/projects/ja3/ashen/venv/bin/activate
python /software/projects/ja3/ashen/gaskap-oh/modules/sidelobe_rejection.py \
    /software/projects/ja3/ashen/gaskap-oh/sofiax.ini
