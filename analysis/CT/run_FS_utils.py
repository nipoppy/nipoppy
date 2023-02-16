import os
import subprocess
import argparse
from pathlib import Path
import shutil
import pandas as pd

# Make sure FS_LICENSE is defined in the container.
os.environ['SINGULARITYENV_FS_LICENSE'] = "/fsdir/license.txt"
os.environ['SINGULARITYENV_SUBJECTS_DIR'] = "/fsdir/"


def get_mris_preproc_cmd(FS_dir, participants_list, out_file, meas="thickness", fwhm=0, template="fsaverage"):
    """ A function to generate FreeSurfer's mris_preproc command
    """
    participants_str_list = []
    for participant in participants_list:
        dirpath = Path(f"{FS_dir}/{participant}")
        dirpath_status = Path.is_dir(dirpath)
        if dirpath_status:
            participants_str_list.append(f"--s {participant}")

    participants_str = ' '.join(participants_str_list)
    FS_CMD_dict = {}
    for hemi in ["lh", "rh"]:
        d = os.path.dirname(out_file)
        f = os.path.basename(out_file)
        hemi_out_file = f"{d}/{hemi}_{f}"

        FS_CMD = f"mris_preproc {participants_str} --target {template} --hemi {hemi} --meas {meas} --fwhm {fwhm} --out {hemi_out_file}"
        FS_CMD_dict[hemi] = FS_CMD

    return FS_CMD_dict
        

def run(FS_dir, participants_list, out_file, meas, fwhm, template):
    """ function to exectute FS container with mris_preproc command
    """
    FS_CMD_dict = get_mris_preproc_cmd(FS_dir, participants_list, out_file, meas, fwhm, template)
    for hemi, FS_CMD in FS_CMD_dict.items():
        print(f"hemisphere: {hemi}")
        CMD_ARGS = SINGULARITY_CMD + FS_CMD 

        CMD = CMD_ARGS.split()

        try:        
            proc = subprocess.run(CMD)

        except Exception as e:
            print(f"mris_preproc run failed with exceptions: {e}")

        print("-"*30)
        print("")

if __name__ == '__main__':
    # argparse
    HELPTEXT = """
    Script to perform DICOM to BIDS conversion using HeuDiConv
    """
    parser = argparse.ArgumentParser(description=HELPTEXT)

    parser.add_argument('--FS_dir', type=str, help='list of participants to process')
    parser.add_argument('--participants_csv', type=str, help='list of participants to process')
    parser.add_argument('--group', type=str, help='filter participants based on a specific group value in the csv')
    parser.add_argument('--output_dir', type=str, help='out_file path for the processed / aggregated output')
    parser.add_argument('--meas', type=str, default="thickness", help='cortical measure')
    parser.add_argument('--fwhm', type=int, default=0, help='smoothing kernel in mm')
    parser.add_argument('--template', type=str, default="fsaverage", help='freesurfer template (fsaverage or fsaverage5)')
    parser.add_argument('--container', type=str, help='path to freesurfer container')

    args = parser.parse_args()

    FS_dir = args.FS_dir
    FS_license = f"{FS_dir}/license.txt"

    participants_csv = args.participants_csv
    group = args.group
    output_dir = args.output_dir
    container = args.container
    meas = args.meas
    fwhm = args.fwhm
    template = args.template
    
    # Singularity CMD 
    SINGULARITY_CMD=f"singularity exec -B {FS_dir}:/fsdir -B {output_dir}:/output_dir {container} "

    _df = pd.read_csv(participants_csv)

    # remove missing MRI participants
    _df = _df[~_df["bids_id"].isna()]

    print("")
    print("-"*50)
    print("Starting FS utils")

    if group is None:
        print("No group filter specified, concatenating all participants")
        participants_list = list(_df["bids_id"])
        group = "all"
    else:
        print(f"Using {group} subset of participants")
        participants_list = list(_df[(_df["group"] == group)]["bids_id"])

    if str(participants_list[0])[:3] != "sub":
        print("Adding sub prefix to the participant_id(s)")
        participants_list = ["sub-" + str(id) for id in participants_list]

    print(f"n_participants: {len(participants_list)}")
    out_file = f"/output_dir/surf_concat_{group}_{fwhm}mm.mgh"

    run(FS_dir, participants_list, out_file, meas, fwhm, template)
    
    print("Running mris_preproc separately for left and right hemisphere\n")
    
    print(" -"*30)
    print("")
    

    print("mris_preproc run complete")
    print("-"*50)
    