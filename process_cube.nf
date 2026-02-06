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
    errorStrategy 'ignore'
    executor = 'slurm'
    clusterOptions = '--ntasks=1 --cpus-per-task=8 --mem=80G --account=ja3 --time=2:00:00'

    input:
        val parameter_file

    output:
        val parameter_file, emit: parameter_file

    script:
        """
        #!/bin/bash

        export OMP_NUM_THREADS=8
        module load wcslib/7.3
        /software/projects/ja3/ashen/SoFiA-2/sofia $parameter_file
        """
}

process update_sofiax_config {
    executor = 'slurm'
    clusterOptions = '--mem=16G --account=ja3 --time=1:00:00'

    input:
        val run_name
        val sofiax_config
        val output_file
        val s2p_setup

    output:
        val output_file, emit: output_file
        val s2p_setup, emit: output_dir

    script:
        """
        #!/bin/bash
        source /software/projects/ja3/ashen/venv/bin/activate
        python3 /software/projects/ja3/ashen/pipeline_components/source_finding/update_sofiax_config.py \
            --config $sofiax_config \
            --output $output_file \
            --run_name $run_name
        """
}

process update_spectra {
    executor = 'slurm'
    clusterOptions = '--mem=32G --account=ja3 --time=12:00:00'

    input:
        val sofiax_config
        val ready

    output:
        val true, emit: done

    script:
        """
        #!/bin/bash
        source /software/projects/ja3/ashen/venv/bin/activate
        python /software/projects/ja3/ashen/gaskap-oh/modules/extract_spectra.py $sofiax_config
        """
}

process sofiax {
    executor = 'slurm'
    clusterOptions = '--mem=32G --account=ja3 --time=2:00:00'

    input:
        val parameter_file
        val sofiax_config
        val ready

    output:
        val true, emit: done

    script:
        """
        #!/bin/bash
        source /software/projects/ja3/ashen/venv/bin/activate
        python /software/projects/ja3/ashen/SoFiAX/sofiax -c $sofiax_config -p ${parameter_file.join(' ')}
        """
}

workflow {
    run = 'gaskap-oh-subregion2_sofiax_pipeline'
    cube = '/scratch/ja3/jkumar/G335_1665/70731-G335-mainline-May2025/ImageCubes/image.restored.i.G334_1666_A_1.SB70731.cube_1665.contsub.fits'
    weights = '/scratch/ja3/jkumar/G335_1665/70731-G335-mainline-May2025/ImageCubes/weights.i.G334_1666_A_1.SB70731.cube_1665.contsub.fits'
    s2p_template = '/software/projects/ja3/ashen/gaskap-oh/s2p_setup.ini'
    sofiax_config = '/software/projects/ja3/ashen/gaskap-oh/sofiax.ini'
    sofia_parameters = '/software/projects/ja3/ashen/gaskap-oh/sofia_template.par'
    sofiax_run_config = '/scratch/ja3/ashen/gaskap-oh/gaskap-oh-subregion2_sofiax_pipeline/sofiax.ini'
    output_dir = '/scratch/ja3/ashen/gaskap-oh/gaskap-oh-subregion2_sofiax_pipeline/outputs'
    products_dir = '/scratch/ja3/ashen/gaskap-oh/gaskap-oh-subregion2_sofiax_pipeline/products'

    main:
        s2p_setup(run, cube, weights, sofia_parameters, s2p_template, output_dir, products_dir)
        update_sofiax_config(run, sofiax_config, sofiax_run_config, s2p_setup.out.output_dir)
        get_parameter_files(s2p_setup.out.output_dir)
        sofia(get_parameter_files.out.parameter_files.flatten())
        sofiax(sofia.out.parameter_file.collect(), update_sofiax_config.out.output_file, true)
}