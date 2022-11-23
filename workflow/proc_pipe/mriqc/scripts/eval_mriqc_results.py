import sys
import json
import glob
import pandas as pd


def eval_mriqc(args): #config file 
    config = json.load(open(args[1])) 
    participants = pd.read_csv(config['subject_list'], sep='\t')
    
    for index in range(1,len(participants)+1):
        output_log = config['input_dir'] + '/mriqc_out_' + str(index) + '.log'
        f = open(output_log, 'r')

        subject_id = f.readline().strip()

        results = {'participant_id': [subject_id], 'T1w': [], 'BOLD': []}
        results.update({a: [] for a in config['file_names']})
    
        f = open(output_log,  "r")
        if "Participant level finished successfully." in f.read():
    
            for arg in results:
            
                acq2 = None
                if arg == 'participant_id': continue
                elif arg == 'T1w': 
                    acq1 = config['input_dir'] + '/' + subject_id + '_ses-*_run-*_T1w*'
            
                elif arg == 'BOLD': 
                    acq1 = config['input_dir'] + '/' + subject_id + '_ses-*_task-rest_run-*_bold*'
                
                else:
                    acq1 = config['input_dir'] + '/' + subject_id + '_ses-*_' + arg + '_run-*_T1w*'
                    acq2 = config['input_dir'] + '/' + subject_id + '_ses-*_' + arg + '_run-*_T2w*'

                if glob.glob(acq1):
                    results[arg].append('Success')
                else: 
                    if acq2:
                        if glob.glob(acq2):
                            results[arg].append('Success')
                        else: results[arg].append('Fail')
                    
                    else: results[arg].append('Fail')
                
        else: 
            for a in results: 
                if a == 'participant_id': continue
                results[a].append('Fail')
    
        df = pd.DataFrame(results)
        if glob.glob(config['results_file']):
            df.to_csv(config['results_file'], mode='a', index=False, header=False)
        else: df.to_csv(config['results_file'], index=False)

eval_mriqc(sys.argv)

