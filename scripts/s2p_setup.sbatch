#!/bin/bash
#SBATCH --account=ja3
#SBATCH --mem-per-cpu=32G
#SBATCH --time=1:00:00
module load /software/projects/ja3/ashen/venv/bin/activate
python3 -u /software/projects/ja3/ashen/s2p_setup/s2p_setup.py \
    --run_name gaskap-oh-subregion2 \
    --config /software/projects/ja3/ashen/gaskap-oh/s2p_setup.ini \
    --image_cube /scratch/ja3/whi550/GASKAP-OH/70731-G335-mainline-May2025/1665/image.restored.i.G334_1666_A_1.SB70731.cube_1665.contsub.fits \
    --weights_cube /scratch/ja3/whi550/GASKAP-OH/70731-G335-mainline-May2025/1665/weights.i.G334_1666_A_1.SB70731.cube_1665.fits.contsub.fits \
    --sofia_template /software/projects/ja3/ashen/gaskap-oh/sofia_template.par \
    --output_dir /scratch/ja3/ashen/gaskap-oh/subregion2/outputs \
    --products_dir /scratch/ja3/ashen/gaskap-oh/subregion2/products
