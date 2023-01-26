import sys
import json
import glob
import pandas as pd
import logging


def eval_mriqc(args): 

    #load config file
    config = json.load(open(args[1])) 
    participants = pd.read_csv(config['subject_list'], sep='\t')
    #subject_id = participants['participant_id'][int(args[-1])+1]
    
    logging.basicConfig(filename='%s/mriqc_eval_err.log'%config['results_dir'], level=logging.DEBUG)
   
    for index in range(len(participants)):
    
    	#get subject ID
    	subject_id = participants['participant_id'][index]
    	
        #read MRIQC pipeline output log
        output_log = config['input_dir'] + '/mriqc_out_' + str(subject_id.split('-')[-1]) + '.log'
        f = open(output_log, 'r')


        logging.info(subject_id)

        results = {'participant_id': [subject_id], 'session_id': [config['session_id']], 'T1w': [], 'BOLD': []} #default datatypes
        results.update({a: [] for a in config['file_names']})
    
        
        #check if participant successfully passed MRIQC pipeline
        if "Participant level finished successfully." in f.read(): 
    
            for arg in results:
            
                acq2 = None
                if arg == 'participant_id' or arg == 'session_id': continue
                
                elif arg == 'T1w': #default check
                    acq1 = config['input_dir'] + '/' + subject_id + '_ses-' + config['session_id'] + '*_run-*_T1w*'
            
                elif arg == 'BOLD': #default check 
                    acq1 = config['input_dir'] + '/' + subject_id + '_ses-' + config['session_id'] + '*_task-rest_run-*_bold*'
                
                else: #check for unknown datatypes
                    acq1 = config['input_dir'] + '/' + subject_id + '_ses-' + config['session_id'] + '*_' + arg + '_run-*_T1w*'
                    acq2 = config['input_dir'] + '/' + subject_id + '_ses-' + config['session_id'] + '*_' + arg + '_run-*_T2w*'

                if glob.glob(acq1):
                    results[arg].append('Success')
                else: 
                    if acq2:
                        if glob.glob(acq2):
                            results[arg].append('Success')
                        else: results[arg].append('Fail')
                    
                    else: results[arg].append('Fail')
                
        else: #no sign participant passed, assume failure for all datatypes
            for a in results: 
                if a == 'participant_id' or a == 'session_id': continue
                results[a].append('Fail')
    
        logging.info(results)
        
        #create/append to csv file
        df = pd.DataFrame(results)
        first_column = df.pop('participant_id')
        second_column = df.pop('session_id')
        df.insert(0, 'participant_id', first_column)
        df.insert(1, 'session_id', second_column)


        results_file = config['results_dir'] + '/' + config['csv_name'] + '.csv'
        if glob.glob(results_file):

            df.to_csv(results_file, mode='a', index=False, header=False)
        else: df.to_csv(results_file, index=False)

eval_mriqc(sys.argv)

