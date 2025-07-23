#!/usr/bin/env nextflow
nextflow.enable.dsl = 2

process s2p_setup {
    input:
        val run_name
        val image_cube
        val weights_cube
        val sofia_parameters
        val s2p_template
        val output_dir
        val products_dir

    output:
        val output_dir, emit: output_dir

    script:
        """
        #!/bin/bash
        module load py-astropy/5.1
        python3 /software/projects/ja3/ashen/s2p_setup/s2p_setup.py \
            --config $s2p_template \
            --image_cube $image_cube \
            --weights_cube $weights_cube \
            --run_name $run_name \
            --sofia_template $sofia_parameters \
            --output_dir $output_dir \
            --products_dir $products_dir
        """
}

process get_parameter_files {
    executor = 'local'

    input:
        val directory

    output:
        val parameter_files, emit: parameter_files

    exec:
        parameter_files = file("$directory/sofia_*.par")
}

process sofia {
    executor = 'slurm'
    clusterOptions = '--ntasks=1 --cpus-per-task=8 --mem=32G --account=ja3 --time=2:00:00'

    input:
        val parameter_file

    script:
        """
        #!/bin/bash

        export OMP_NUM_THREADS=8
        module load wcslib/7.3
        /software/projects/ja3/ashen/SoFiA-2/sofia $parameter_file
        """
}

workflow {
    run = 'gaskap-oh-subregion2'
    cube = '/scratch/ja3/whi550/GASKAP-OH/70731-G335-mainline-May2025/1665/image.restored.i.G334_1666_A_1.SB70731.cube_1665.contsub.fits'
    weights = '/scratch/ja3/whi550/GASKAP-OH/70731-G335-mainline-May2025/1665/weights.i.G334_1666_A_1.SB70731.cube_1665.fits.contsub.fits'
    s2p_template = '/software/projects/ja3/ashen/gaskap-oh/s2p_setup.ini'
    sofia_parameters = '/software/projects/ja3/ashen/gaskap-oh/sofia_template.par'
    output_dir = '/scratch/ja3/ashen/gaskap-oh/subregion2/outputs'
    products_dir = '/scratch/ja3/ashen/gaskap-oh/subregion2/products'

    main:
        s2p_setup(run, cube, weights, sofia_parameters, s2p_template, output_dir, products_dir)
        get_parameter_files(s2p_setup.out.output_dir)
        sofia(get_parameter_files.out.parameter_files.flatten())
}