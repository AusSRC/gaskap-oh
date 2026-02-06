#!/bin/bash
#SBATCH --account=ja3
#SBATCH --time=12:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=8

module load nextflow/24.10.0
unset SLURM_MEM_PER_CPU
unset SLURM_MEM_PER_NODE

export NXF_DEBUG=2
export PYTHON_ENV=/software/projects/ja3/ashen/venv/bin/activate
export SOFTWARE_DIR=/software/projects/ja3/ashen

nextflow run process_cube.nf -with-trace -resume
