import os
import subprocess
import argparse
from pathlib import Path
import shutil
import pandas as pd

def get_mris_preproc_cmd(participants_list, out_file, meas="thickness", template="fsaverage"):
    """ A function to generate FreeSurfer's mris_preproc command
    """
    participants_str_list = []
    for participant in participants_list:
        participants_str_list.append(f"--s sub-{participant}")

    participants_str = ' '.join(participants_str_list)
    FS_CMD_dict = {}
    for hemi in ["lh", "rh"]:
        d = os.path.dirname(out_file)
        f = os.path.basename(out_file)
        out_file = f"{d}/{hemi}_{f}"

        FS_CMD = f"mris_preproc {participants_str} --target {template} --hemi {hemi} --meas {meas} --out {out_file}"
        FS_CMD_dict[hemi] = FS_CMD

    return FS_CMD_dict
        

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
    template = args.template

    # Make sure FS_LICENSE is defined in the container.
    os.environ['SINGULARITYENV_FS_LICENSE'] = "/fsdir/license.txt"
    os.environ['SINGULARITYENV_SUBJECTS_DIR'] = "/fsdir/"
    
    # Singularity CMD 
    SINGULARITY_CMD=f"singularity exec -B {FS_dir}:/fsdir -B {output_dir}:/output_dir {container} "

    participants_df = pd.read_csv(participants_csv)
    print("")
    print("-"*50)
    print("Starting FS utils")
    
    if group is None:
        print("No group filter specified, concatenating all participants")
        participants_list = list(participants_df["bids_id"])
        group = "all"
    else:
        print(f"Using {group} subset of participants")
        participants_list = list(participants_df[participants_df["group"] == group]["bids_id"])

    print(f"n_participants: {len(participants_list)}")
    out_file = f"/output_dir/surf_concat_{group}.mgh"

    FS_CMD_dict = get_mris_preproc_cmd(participants_list, out_file, meas, template)
    
    print("Running mris_preproc separately for left and right hemisphere\n")
    
    print("-"*30)
    print("")
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

    print("mris_preproc run complete")
    print("-"*50)
    