import subprocess
import argparse
# import json

parser = argparse.ArgumentParser(description='')

parser.add_argument('--global_config', type=str, help='path to global configs for a given nipoppy dataset')
parser.add_argument('--output_dir', type=str, help='overwrite path to put results in case of issues with default')
parser.add_argument('--participant_id', type=str, help='subject ID to be processed')
parser.add_argument('--session_id', type=str, help='session ID to be processed')

args = parser.parse_args()

DATASET_ROOT = args.global_config["DATASET_ROOT"]
CONTAINER_STORE = args.global_config["CONTAINER_STORE"]
#is currently mriqc_patch.simg
MRIQC_CONTAINER = args.global_config["PROC_PIPELINES"]["mriqc"]["CONTAINER"]

# config = json.load(open(args.global_config))

output_dir = args.output_dir
participant_id = args.participant_id
session_id = args.session_id

subprocess.run([f"echo subject: {participant_id} session: {session_id} >> {output_dir}/mriqc_out_{participant_id}.log"], shell=True)

subprocess.run([f"singularity run --cleanenv -B {DATASET_ROOT}:/data:ro -B {output_dir}:/out --no-sub /data /out \
                {CONTAINER_STORE}/{MRIQC_CONTAINER} participant --participant-label {participant_id} --session-id {session_id} \
                >> {output_dir}/mriqc_out_{participant_id}.log"], shell=True)

