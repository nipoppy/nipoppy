import subprocess
import argparse
import pandas as pd

parser = argparse.ArgumentParser(description='')

parser.add_argument('--global_config', type=str, help='path to global configs for a given mr_proc dataset')
parser.add_argument('--results_dir', type=str, help='path to where to store MRIQC output') 
parser.add_argument('--participant_list', type=str, help='path to file containing subjects to test') #participants.tsv
parser.add_argument('--index', type=int, help='index for participant list')
parser.add_argument('--container', type=str, help='path to where container is located')

args = parser.parse_args()

global_config = args.global_config
container = args.container
results_dir = args.results_dir
index = args.index
participant_list = pd.read_csv(args.participant_list) #pd.read_csv(global_config + '/' + args.participant_list)
participant_id = participant_list.loc[index]['participant_id']
participant_label = participant_id.split('-')[-1]

subprocess.run(['echo %s >> %s/mriqc_out_%s.log'%(participant_id, results_dir, participant_label)], shell=True)

subprocess.run(['singularity run --cleanenv -B %s:/data:ro -B %s:/out %s --no-sub /data /out participant --participant-label %s >> %s/mriqc_out_%s.log'%(global_config, results_dir, container, participant_id, results_dir, participant_label)], shell=True)

