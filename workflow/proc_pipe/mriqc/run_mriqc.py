import subprocess
import argparse
import pandas as pd
import json

parser = argparse.ArgumentParser(description='')

parser.add_argument('--global_config', type=str, help='path to global configs for a given mr_proc dataset')
parser.add_argument('--output_dir', type=str, help='overwrite path to put results in case of issues with default')
args = parser.parse_args()

config = json.load(open(args.global_config))

output_dir = args.output_dir
if output_dir: results_dir = output_dir
else: results_dir = config['DATASET_ROOT'] + '/derivatives/mriqc/22.0.1/output/'

container = config['CONTAINER_STORE']
index = config['INDEX']
participant_list = pd.read_csv('/tabular/demographics/mr_proc_recruitment_manifest.csv')
participant_id = participant_list.loc[index]['bids_id']
participant_label = participant_id.split('-')[-1]

subprocess.run(['echo %s >> %s/mriqc_out_%s.log'%(participant_id, results_dir, participant_label)], shell=True)

subprocess.run(['singularity run --cleanenv -B %s:/data:ro -B %s:/out %s --no-sub /data /out participant --participant-label %s >> %s/mriqc_out_%s.log'%(config['DATASET_ROOT'], results_dir, container, participant_id, results_dir, participant_label)], shell=True)

