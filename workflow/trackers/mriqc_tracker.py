import sys
import json
import glob

PIPELINE_NAME = 'MRIQC'
PIPELINE_VERSION = '22.0.1'
PIPELINE_STARTTIME = '2023-01-23 00:00:00'


def eval_mriqc(args):
    
    #load config file
    config = json.load(open(args[1])) 
    
    #check if there's additional arguments
    if 'pipeline_name' in config.keys():
        PIPELINE_NAME = config['pipeline_name']
    if 'pipeline_version' in config.keys():
        PIPELINE_VERSION = config['pipeline_version']
    if 'pipeline_starttime' in config.keys():
        PIPELINE_STARTTIME = config['pipeline_starttime']

    

    #read MRIQC pipeline output log
    output_log = config['input_dir'] + '/mriqc_out_' + str(config['subject_id']) + '.log'
    f = open(output_log, 'r')


    results = {'participant_id': [config['subject_id']], 'session': [config['session_id']], 
               'pipeline_name': [PIPELINE_NAME], 'pipeline_version': [PIPELINE_VERSION], 
               'pipeline_starttime': [PIPELINE_STARTTIME], 'PIPELINE_STATUS_COLUMNS': []} 
    
        
    #check if participant successfully passed MRIQC pipeline
    if "Participant level finished successfully." in f.read(): 
        
        acq_T1w = config['input_dir'] + '/' + config['subject_id'] + '_ses-' + config['session_id'] + '*_run-*_T1w*'
        
        if glob.glob(acq_T1w):
                results['PIPELINE_STATUS_COLUMNS'].append('SUCCESS')
        else: results['PIPELINE_STATUS_COLUMNS'].append('FAIL')
            
    
    else: #no sign participant passed, assume failure for all datatypes
        results['PIPELINE_STATUS_COLUMNS'].append('FAIL')
        
    return results


def check_bold(args):
    
    #load config file
    config = json.load(open(args[1])) 
    
    #read MRIQC pipeline output log
    output_log = config['input_dir'] + '/mriqc_out_' + str(config['subject_id']) + '.log'

    f = open(output_log, 'r')
    
    if "Participant level finished successfully." in f.read(): 
        acq_bold = config['input_dir'] + '/' + config['subject_id'] + '_ses-' + config['session_id'] + '*_task-rest_run-*_bold*'
    
        if glob.glob(acq_bold):
                return 'SUCCESS'
        else: return 'FAIL'

    else: #no sign participant passed, assume failure for all datatypes
        return 'FAIL'
         

tracker_configs = {
    "pipeline_complete": eval_mriqc(sys.argv),
    
    "Stage_": {
            "MRIQC_BOLD": check_bold(sys.argv)
            }
}


