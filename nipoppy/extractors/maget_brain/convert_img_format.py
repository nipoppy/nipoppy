import os
import sys
import argparse
import glob
import subprocess

print("-"*50)
print("This script requires minc-tools")
print("-"*50)


# argparse
HELPTEXT = """
Script to convert between nii and mnc (either way) using minc-tools
"""
parser = argparse.ArgumentParser(description=HELPTEXT)
parser.add_argument('--nii_dir', type=str, required=True, help='path to nii dir')
parser.add_argument('--mnc_dir', type=str, required=True, help='path to mnc dir')
parser.add_argument('--conv_script', type=str, required=True, help='nii2mnc or mnc2nii')

args = parser.parse_args()
nii_dir = args.nii_dir
mnc_dir = args.mnc_dir
conv_script = args.conv_script

print(f"nii dir: {nii_dir}\nmnc_dir: {mnc_dir}\nconv_script: {conv_script}")
print("-"*50)

if conv_script in ["nii2mnc"]:
    input_file_list = glob.glob(f"{nii_dir}/*.nii*")
    output_dir = mnc_dir
    out_file_suffix = "mnc"
else:
    input_file_list = glob.glob(f"{mnc_dir}/*.mnc")
    output_dir = nii_dir
    out_file_suffix = "nii"

print(f"number of input files: {len(input_file_list)}")

for input_file in input_file_list:
    # parse output file name
    f = os.path.basename(input_file)
    out_file_prefix = f.split(".")[0]
    output_file = f"{output_dir}/{out_file_prefix}.{out_file_suffix}"

    print(f"input file: {input_file}\noutput file: {output_file}")

    # convert
    if conv_script in ["nii2mnc"]:
        CMD = ["nii2mnc", "-short", f"{input_file}", f"{output_file}"]
        subprocess.run(CMD, check=True)
    
    elif conv_script in ["mnc2nii"]:
        CMD = ["mnc2nii", "-short", "-nii", f"{input_file}", f"{output_file}"]
        gzip_CMD = ["gzip", f"{output_file}"]
        subprocess.run(CMD, check=True)
        subprocess.run(gzip_CMD, check=True)

    else:
        print(f"Unknown conversion argument: {conv_script}")
