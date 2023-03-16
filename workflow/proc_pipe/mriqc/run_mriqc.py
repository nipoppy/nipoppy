import subprocess
import argparse
import json

parser = argparse.ArgumentParser(description='')

parser.add_argument('--global_config', type=str, help='path to global configs for a given mr_proc dataset')
parser.add_argument('--output_dir', type=str, help='overwrite path to put results in case of issues with default')
args = parser.parse_args()

config = json.load(open(args.global_config))

output_dir = args.output_dir

subprocess.run(['echo %s >> %s/mriqc_out_%s.log'%(config['subject_id'], output_dir, config['subject_id'])], shell=True)

subprocess.run(['singularity run --cleanenv -B %s:/data:ro -B %s:/out %s --no-sub /data /out participant --participant-label %s >> %s/mriqc_out_%s.log'%(config['input_dir'], output_dir, config['container_dir'], config['subject_id'], output_dir, config['subject_id'])], shell=True)

