import argparse
import subprocess
from xxlimited import Str
import pandas as pd
from pathlib import Path
import os
import glob
import shutil
import pydicom

HELPTEXT = """
Script to perform DICOM to BIDS conversion using HeuDiConv
"""
#Author: nikhil153
#Date: 07-Oct-2022

# argparse
parser = argparse.ArgumentParser(description=HELPTEXT)

parser.add_argument('--filename_map_csv', type=str, help='path to the CSV file containing map between raw dicom directory name --> participant name')
parser.add_argument('--filename_pattern', type=str, default="", help='filename_pattern to filter raw dicom files')
parser.add_argument('--output_dir', type=str, help='path to the output directory to save reorganized dicoms')
parser.add_argument('--remove_raw_dicom', default=False, action=argparse.BooleanOptionalAction, help='remove raw dicoms to save sapce')
parser.add_argument('--test_run', default=False, action=argparse.BooleanOptionalAction, help='do a test run with a single raw dicom dir')

args = parser.parse_args()

filename_map_csv = args.filename_map_csv
filename_pattern = args.filename_pattern
output_dir = args.output_dir
remove_raw_dicom = args.remove_raw_dicom
test_run = args.test_run

map_df = pd.read_csv(filename_map_csv)
if test_run:
    map_df = map_df.head(1)
    print(f"\nDoing a test run with single raw dicom dir")
else:
    print(f"\nNumber of participants to be organized: {len(map_df)}")

if remove_raw_dicom:
    print(f"\n***Source raw dicom dirs will be deleted after remaming***")

for index, row in map_df.iterrows():
    raw_participant_dir = row["raw_dir_name"]
    participant_id = row["participant_id"]

    if not Path(raw_participant_dir).is_dir():
        print(f"{raw_participant_dir} is missing for {participant_id}...")

    else:
        print(f"\n***Starting dicom reorganization for {participant_id}***\n")
        
        try:
            filepaths = []
            for root, dirnames, filenames in os.walk(f"{raw_participant_dir}"):
                for filename in filenames:
                    filepaths.append(os.path.join(root, filename))

            n_raw_dicoms = len(filepaths)    
            print(f"Number of dicoms found: {n_raw_dicoms}")

            participant_dicom_dir = f"{output_dir}/{participant_id}"

            if not Path(participant_dicom_dir).is_dir():
                os.mkdir(participant_dicom_dir)

            print(f"Copying renamed dicom files into: {participant_dicom_dir}")
            dcm_idx = 1
            dst_filename_len = len(str(n_raw_dicoms))
            skipped_file_list = []
            for src_fpath in filepaths:
                if (filename_pattern == "") | (filename_pattern in src_fpath):      
                    # check if the file is vaild dicom
                    try:
                        dataset = pydicom.dcmread(src_fpath)                
                        dst_filename = str(dcm_idx).zfill(dst_filename_len)
                        dst_fpath = f"{participant_dicom_dir}/{dst_filename}.dcm"
                        shutil.copyfile(src_fpath, dst_fpath)
                        dcm_idx += 1
                    except:
                        print(f"Error reading {src_fpath}. Not renaming it.")
                        skipped_file_list.append(f"{src_fpath},invalid_dicom")

                else:
                    skipped_file_list.append(f"{src_fpath},filename_pattern_mismatch")

            skipped_files_txt = f"{output_dir}/{participant_id}_skipped_files.csv"
            with open(skipped_files_txt, 'w') as output_file:
                for line in skipped_file_list:
                    output_file.write(line + '\n')

            print(f"Number of files skipped: {len(skipped_file_list)}. See list here: {skipped_files_txt}")

            if remove_raw_dicom:                
                shutil.rmtree(raw_participant_dir)

        except Exception as ex:
            print(ex)

    print(f"\n***Ending dicom reorganization for {participant_id}***")
