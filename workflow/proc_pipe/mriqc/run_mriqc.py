import subprocess
import argparse
# import json

parser = argparse.ArgumentParser(description='')

parser.add_argument('--global_configs', type=str, help='path to global configs for a given mr_proc dataset')
parser.add_argument('--output_dir', type=str, help='overwrite path to put results in case of issues with default')
parser.add_argument('--subject_id', type=str, help='subject ID to be processed')

args = parser.parse_args()

DATASET_ROOT = args.global_configs["DATASET_ROOT"]
CONTAINER_STORE = args.global_configs["CONTAINER_STORE"]

# config = json.load(open(args.global_config))

output_dir = args.output_dir
subject_id = args.subject_id

subprocess.run(['echo %s >> %s/mriqc_out_%s.log'%(subject_id, output_dir, subject_id)], shell=True)

subprocess.run(['singularity run --cleanenv -B %s:/data:ro -B %s:/out %s --no-sub /data /out participant --participant-label %s >> %s/mriqc_out_%s.log'%(DATASET_ROOT, output_dir, CONTAINER_STORE, subject_id, output_dir, subject_id)], shell=True)

