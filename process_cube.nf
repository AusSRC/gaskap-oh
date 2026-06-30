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
        python3 $SOFTWARE_DIR/s2p_setup/s2p_setup.py \
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
    clusterOptions = '--mem=128G --account=ja3 --time=8:00:00'
    // subcube shape is currently 2000x2000x4000 (64 GB)

    input:
        val parameter_file

    output:
        val parameter_file, emit: parameter_file

    script:
        """
        #!/bin/bash

        export OMP_NUM_THREADS=8
        module load wcslib/7.3
        $SOFTWARE_DIR/SoFiA-2/sofia $parameter_file
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
        source $PYTHON_ENV
        python3 $SOFTWARE_DIR/pipeline_components/source_finding/update_sofiax_config.py \
            --config $sofiax_config \
            --output $output_file \
            --run_name $run_name
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
        source $PYTHON_ENV
        python $SOFTWARE_DIR/SoFiAX/sofiax -c $sofiax_config -p ${parameter_file.join(' ')}
        """
}

process summary_plots {
    executor = 'slurm'
    clusterOptions = '--mem=16G --account=ja3 --time=2:00:00'

    input:
        val products_dir
        val ready

    output:
        val true, emit: done

    script:
        """
        #!/bin/bash
        source $PYTHON_ENV
        python $SOFTWARE_DIR/gaskap-oh/modules/plotly_plots.py $products_dir
        """
}

process sidelobe_rejection {
    executor = 'slurm'
    clusterOptions = '--mem=16G --account=ja3 --time=2:00:00'

    input:
        val sofiax_config
        val ready

    output:
        val true, emit: done

    script:
        """
        #!/bin/bash
        source $PYTHON_ENV
        python $SOFTWARE_DIR/gaskap-oh/modules/sidelobe_rejection.py $sofiax_config
        """
}

workflow {
    // User-provided parameters
    run = params.RUN
    workdir = params.WORKDIR ?: "/scratch/ja3/ashen/gaskap-oh/${run}"
    cube = params.CUBE
    weights = params.WEIGHTS

    // Temporary files
    output_dir = "${workdir}/outputs"
    products_dir = "${workdir}/products"
    sofiax_run_config = "${workdir}/sofiax.ini"

    // User configuration
    dir = System.getProperty("user.dir");
    s2p_template = "${dir}/config/s2p_setup.ini"
    sofiax_config = "${dir}/config/sofiax_upd.ini"
    sofia_parameters = "${dir}/config/sofia_template.par"

    main:
	// Setup
        s2p_setup(run, cube, weights, sofia_parameters, s2p_template, output_dir, products_dir)
        update_sofiax_config(run, sofiax_config, sofiax_run_config, s2p_setup.out.output_dir)
        get_parameter_files(s2p_setup.out.output_dir)

	// Run SoFiA and SoFiAX
        sofia(get_parameter_files.out.parameter_files.flatten())
        summary_plots(products_dir, sofia.out.parameter_file.collect())
        sofiax(sofia.out.parameter_file.collect(), update_sofiax_config.out.output_file, summary_plots.out.done)

	// Run sidelobe rejection
        sidelobe_rejection(update_sofiax_config.out.output_file, sofiax.out.done)
}
