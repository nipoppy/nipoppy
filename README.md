[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.8084759.svg)](https://doi.org/10.5281/zenodo.8084759)

# nipoppy 

A workflow manager for curating MRI and tabular data and standardized processing. 

_Pull-Organize-Process-Push-Yey!_

**Note: This is a nimhans-YLO dataset-specifc fork**

## Documentation

### nipoppy modules

- [nipoppy](https://neurobagel.org/nipoppy/overview/)

### Individual containerized pipelines:

- [Heudionv](https://heudiconv.readthedocs.io/en/latest/installation.html#singularity) 
- [MRIQC](https://mriqc.readthedocs.io/en/stable/)
- [fMRIPrep](https://fmriprep.org/en/1.5.5/singularity.html) 
- [TractoFlow](https://github.com/scilus/tractoflow)
- [MAGeT Brain](https://github.com/CoBrALab/MAGeTbrain)

---

## Quickstart (How to run a preset workflow setup)
### Onetime setup
1. Project
   - Create a project dir on your local machine: `mkdir /home/<user>/projects/<my_project>`
   - Create `containers`, `code`, `data`  dirs inside your project dir.  
2. Containers (Singulaity)
   - Install [Singularity](https://singularity-tutorial.github.io/01-installation/)
   - Download containers (e.g. Heudiconv) for the pipelines used in this workflow inside the `containers` dir. 
3. Code
   - Change dir to `code`: `cd /home/<user>/projects/<my_project>/code/`
   - Create a new [venv](https://realpython.com/python-virtual-environments-a-primer/): `python3 -m venv nipoppy_env` 
   - Activate your env: `source nipoppy_env/bin/activate` 
   - Clone this repo: `git clone https://github.com/neurodatascience/nipoppy-nimhans_YLO.git`
   - Install python dependencies: `pip install -e .`  
4. Data 
   - Change dir to nipoppy scripts: `cd /home/<user>/projects/<my_project>/code/nipoppy/scripts`
   - Create nipoppy dataset-tree: `./nipoppy_setup.sh /home/<user>/projects/<my_project>/data <study_name>`
   - Create and populate `<study_name>/proc/global_configs.json` 
   - Copy your participant-level dicom dirs (e.g. `MNI001`, `MNI002` ...) into `<study_name>/scratch/raw_dicom/`
5. RedCap: configure RedCap access
   
### Periodic runs
1. Change dir to `nipoppy code`: `cd /home/<user>/projects/<my_project>/code/nipoppy`
2. Activate your env: `source nipoppy/bin/activate` (if starting with a new terminal)
3. Run nipoppy: `python run_nipoppy.py --global_config <> --session_id <> --n_jobs <>`

### Expected output
1. `<study_name>/dicom`: Participant-level dirs with symlinks to the dicom files in the raw_dicom dir
   - Note: dicoms that are unreadable or contain derived (i.e. scanner processed) scans will be skipped and enlisted in the `<study_name>/scratch/logs`
2. `<study_name>/bids`: BIDS dataset comprising all the modalities in Nifti format (i.e. nii.gz and sidecar json)

---

### Individual containerized pipelines:

- [Heudionv](https://heudiconv.readthedocs.io/en/latest/installation.html#singularity) 
- [MRIQC](https://mriqc.readthedocs.io/en/stable/)
- [fMRIPrep](https://fmriprep.org/en/1.5.5/singularity.html) 
- [TractoFlow](https://github.com/scilus/tractoflow)
- [MAGeT Brain](https://github.com/CoBrALab/MAGeTbrain)

