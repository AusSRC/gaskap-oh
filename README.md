# GASKAP-OH

## Overview

### Usage



### Sidelobe rejection strategy

![flowchart](media/flow.png)

## Processing

Noting the subregions that have been processed.

### choosing parameters

All of these runs are in the `choose_parameters` subdirectory

### subregion (processing the entire cube)

### running

Process:
* Update `s2p_setup.sh` script run name, output directories
* Update `s2p_setup.ini` file boundary
* run `process_cube.sbatch`

### overview

cube shape: [12254, 10683, 1, 3842]

breaks:
- ra: 0-6127, 6128-12254
- dec: 0-5341, 5342-10683
- freq: 0-960, 961-1920, 1921-2880, 2881-3842

regions:
- subregion1: 0,6127,0,5341,0,960
- subregion2: 0,6127,0,5341,961,1920 (started)
- subregion3: 0,6127,0,5341,1291,2880
- subregion4: 0,6127,0,5341,2881,3842

- subregion5: 6128,12254,0,5341,0,960
- subregion6: 6128,12254,0,5341,961,1920
- subregion7: 6128,12254,0,5341,1291,2880
- subregion8: 6128,12254,0,5341,2881,3842

- subregion9: 0,6127,5342,10683,0,960
- subregion10: 0,6127,5342,10683,961,1920
- subregion11: 0,6127,5342,10683,1291,2880
- subregion12: 0,6127,5342,10683,2881,3842

- subregion13: 6128,12254,5342,10683,0,960
- subregion14: 6128,12254,5342,10683,961,1920
- subregion15: 6128,12254,5342,10683,1291,2880
- subregion16: 6128,12254,5342,10683,2881,3842
