import sys
import json
import glob
import pandas as pd
import logging

PIPELINE_NAME = 'MRIQC'
PIPELINE_VERSION = '22.0.1'
PIPELINE_STARTTIME = '2023-01-23 00:00:00'


def eval_mriqc(args): #
    
    #load config file
    config = json.load(open(args[1])) 
    
    #check if there's additional arguments
    if 'pipeline_name' in config.keys():
        PIPELINE_NAME = config['pipeline_name']
    if 'pipeline_version' in config.keys():
        PIPELINE_VERSION = config['pipeline_version']
    if 'pipeline_starttime' in config.keys():
        PIPELINE_STARTTIME = config['pipeline_starttime']

    
    logging.basicConfig(filename='%s/mriqc_eval_err.log'%config['results_dir'], level=logging.DEBUG)

    #read MRIQC pipeline output log
    output_log = config['input_dir'] + '/mriqc_out_' + str(config['subject_id']) + '.log'
    f = open(output_log, 'r')


    logging.info(config['subject_id'])

    results = {'participant_id': [config['subject_id']], 'session': [config['session_id']], 
               'pipeline_name': [PIPELINE_NAME], 'pipeline_version': [PIPELINE_VERSION], 
               'pipeline_starttime': [PIPELINE_STARTTIME], 'PIPELINE_STATUS_COLUMNS': [], 'MRIQC_BOLD': []} 
    
        
    #check if participant successfully passed MRIQC pipeline
    if "Participant level finished successfully." in f.read(): 
        
        acq_T1w = config['input_dir'] + '/' + config['subject_id'] + '_ses-' + config['session_id'] + '*_run-*_T1w*'
        acq_bold = config['input_dir'] + '/' + config['subject_id'] + '_ses-' + config['session_id'] + '*_task-rest_run-*_bold*'
        
        if glob.glob(acq_T1w):
                results['PIPELINE_STATUS_COLUMNS'].append('SUCCESS')
        else: results['PIPELINE_STATUS_COLUMNS'].append('FAIL')
            
        if glob.glob(acq_bold):
                results['MRIQC_BOLD'].append('SUCCESS')
        else: results['MRIQC_BOLD'].append('FAIL')

    
    else: #no sign participant passed, assume failure for all datatypes
        results['PIPELINE_STATUS_COLUMNS'].append('FAIL')
        results['MRIQC_BOLD'].append('FAIL')
        
    return results
