import numpy as np
import pandas as pd
import os
import glob
import argparse
from freesurfer_stats import CorticalParcellationStats

HELPTEXT = """
Script to parse and collate FreeSurfer stats files across subjects
Author: nikhil153
Date: May-5-2022
"""

# Sample cmd:
#  python collate_freesurfer_stats.py --stat_file aparc.DKTatlas.stats \
#                                     --stat_measure average_thickness_mm \
#                                     --fs_output_dir /home/nikhil/projects/brain_changes/data/adni/derivatives/freesurfer-6.0.1/ \
#                                     --ukbb_dkt_ct_fields ../metadata/UKBB_DKT_CT_Fields.csv \
#                                     --ukbb_aseg_vol_fields ../metadata/UKBB_ASEG_vol_Fields.csv \
#                                     --aseg \
#                                     --save_dir ./

parser = argparse.ArgumentParser(description=HELPTEXT)

# data
# TODO: Not sure how to handle multiple visits..
# parser.add_argument('--participants_list', dest='participants_list',                      
#                     help='path to participants list (csv or tsv')

parser.add_argument('--fs_output_dir', help='path to fs_output_dir with all the subjects')
parser.add_argument('--stat_file', default='aparc.DKTatlas.stats', help='name of a standard FS stat file')
parser.add_argument('--stat_measure', default='average_thickness_mm', help='path to bids_dir')                    
parser.add_argument('--ukbb_dkt_ct_fields', help='UKBB lookup table with fields ID and DKT ROI names')
parser.add_argument('--ukbb_aseg_vol_fields', default="", help='UKBB lookup table with fields ID and ASEG ROI names')
parser.add_argument('--aseg', action='store_true', help='Parse aseg.stats to collate subcortical volumes')
parser.add_argument('--save_dir', default='./', help='path to save_dir')
args = parser.parse_args()

def parse_aseg(aseg_file, stat_measure):
    """Function to parse aseg.stats file from freesurfer"""

    aseg_data = np.loadtxt(aseg_file, dtype="i1,i1,i4,f4,S32,f4,f4,f4,f4,f4")

    aseg_df = pd.DataFrame(data=aseg_data)
    aseg_df = aseg_df[["f4","f3"]].rename(columns={"f3":stat_measure, "f4":"hemi_ROI"})
    aseg_df["hemi_ROI"] = aseg_df["hemi_ROI"].str.decode('utf-8') 

    # print(f"number of ROIs in aseg file: {len(aseg_df)}")

    # Get global volumes from the "measure" lines
    file_data = open(aseg_file, 'r')
    lines = file_data.readlines()
    measure_lines = []
    for line in lines:
        if "Measure" in line:
            measure_lines.append(line)

    global_df = pd.DataFrame(measure_lines)
    global_df = global_df.replace('\n','', regex=True)
    global_df = global_df[0].str.split(",", expand=True)
    global_df[0] = global_df[0].str.split(" ", expand=True)[2]
    global_df[0] = global_df[0].replace({"EstimatedTotalIntraCranialVol":"EstimatedTotalIntraCranial"}) #To match UKB field names
    global_df = global_df[[0,3]]

    global_df = global_df.rename(columns = {0:"hemi_ROI",3:stat_measure})

    aseg_df = pd.concat([aseg_df,global_df],axis=0)

    return aseg_df



if __name__ == "__main__":
    # Read from csv
    fs_output_dir = args.fs_output_dir
    stat_file = args.stat_file
    stat_measure = args.stat_measure
    save_dir = args.save_dir
    ukbb_dkt_ct_fields = args.ukbb_dkt_ct_fields
    ukbb_aseg_vol_fields = args.ukbb_aseg_vol_fields

    aseg = args.aseg

    ukbb_dkt_ct_fields_df = pd.read_csv(ukbb_dkt_ct_fields)

    print(f"Starting to collate {stat_measure} in {fs_output_dir}\n")
    subject_dir_list = glob.glob(f"{fs_output_dir}sub*")
    subject_id_list = [os.path.basename(x) for x in subject_dir_list]

    print(f"Found {len(subject_id_list)} subjects\n")

    ### cortical surface measures 
    print(f"***Parsing ASEG subcortical volumes***")
    hemispheres = ["lh", "rh"]

    hemi_stat_measures_dict = {}
    for hemi in hemispheres:
        stat_measure_df = pd.DataFrame()
        for subject_id in subject_id_list:
            try:
                fs_stats_dir = f"{fs_output_dir}{subject_id}/stats/"
                stats = CorticalParcellationStats.read(f"{fs_stats_dir}{hemi}.{stat_file}").structural_measurements
                
                cols = ["subject_id"] + list(stats["structure_name"].values)
                vals = [subject_id] + list(stats[stat_measure].values)
                
                df = pd.DataFrame(columns=cols)
                df.loc[0] = vals
                stat_measure_df = pd.concat([stat_measure_df, df], axis=0)
            except:
                print(f"Error parsing cortical data for {subject_id} ({hemi})")

        # replace columns names with ukbb field IDs
        field_df = ukbb_dkt_ct_fields_df[ukbb_dkt_ct_fields_df["hemi"]==hemi][["Field ID","roi"]]
        roi_field_id_dict = dict(zip(field_df["roi"], field_df["Field ID"]))
        stat_measure_df = stat_measure_df.rename(columns=roi_field_id_dict)
        
        hemi_stat_measures_dict[hemi] = stat_measure_df

    # merge left and right dfs
    stat_measure_LR_df = pd.merge(hemi_stat_measures_dict["lh"],hemi_stat_measures_dict["rh"], on="subject_id")

    # Drop columns ommited by DKT atlas
    if stat_file == "aparc.DKTatlas.stats":
        drop_ROIs = ["temporalpole","frontalpole","banks of the superior temporal sulcus"]
        for d_roi in drop_ROIs:
            if d_roi in stat_measure_LR_df.columns:
                stat_measure_LR_df = stat_measure_LR_df.drop(columns=[d_roi])

    save_file = f"{stat_file.split('.')[1]}_{stat_measure.rsplit('_',1)[0]}.csv"

    print(f"Saving cortical stat measures here: {save_dir}/{save_file}\n")
    stat_measure_LR_df.to_csv(f"{save_dir}/{save_file}")

    # ASEG subcortical volumes
    if aseg:
        print(f"***Parsing ASEG subcortical volumes***")
        stat_file = "aseg.stats"
        stat_measure = "Volume_mm3"

        # Grab UKBB field ids lookup table
        ukbb_aseg_vol_fields_df = pd.read_csv(ukbb_aseg_vol_fields)
        
        stat_measure_df = pd.DataFrame()
        for subject_id in subject_id_list:
            try: 
                fs_stats_dir = f"{fs_output_dir}{subject_id}/stats/"
                aseg_file = f"{fs_stats_dir}{stat_file}"
                stats = parse_aseg(aseg_file,stat_measure)
                
                cols = ["subject_id"] + list(stats["hemi_ROI"].values)
                vals = [subject_id] + list(stats[stat_measure].values)
                
                df = pd.DataFrame(columns=cols)
                df.loc[0] = vals
                stat_measure_df = pd.concat([stat_measure_df, df], axis=0)

            except:
                print(f"Error parsing subcortical volumes for {subject_id}")

        
        field_df = ukbb_aseg_vol_fields_df[ukbb_aseg_vol_fields_df["hemi_ROI"].isin(stat_measure_df.columns)]
        common_rois = list(field_df["hemi_ROI"].values)
        roi_field_id_dict = dict(zip(field_df["hemi_ROI"], field_df["Field ID"]))

        print(f"Number of aseg vol ROIs after UKBB merge: {len(roi_field_id_dict)}")

        # Rename ROIs with ukbb ids (remove the ROIs which don't have ukbb ids)
        stat_measure_df = stat_measure_df[["subject_id"] + common_rois].copy()
        stat_measure_df = stat_measure_df.rename(columns=roi_field_id_dict)

        save_file = f"aseg_subcortical_volumes.csv"
        
        print(f"Saving subcortical stat measures here: {save_dir}/{save_file}")
        stat_measure_df.to_csv(f"{save_dir}/{save_file}")
