import sys
import json
import glob

def eval_mriqc(subject_dir):
    
       
    subject_id = subject_dir.split('/')[-1].split('-')[-1]
    session_id = [x for x in subject_dir.split('/') if 'ses' in x][0].split('-')[-1]


    #read MRIQC pipeline output log
    output_log = subject_dir + '/mriqc_out_' + str(subject_id) + '.log'
    f = open(output_log, 'r')


    results = {'participant_id': [subject_id], 'session': [session_id], 'PIPELINE_STATUS_COLUMNS': []} 
    
        
    #check if participant successfully passed MRIQC pipeline
    if "Participant level finished successfully." in f.read(): 
        
        acq_T1w = subject_dir + '/' + str(subject_id) + '_ses-' + str(session_id) + '*_run-*_T1w*'
        
        if glob.glob(acq_T1w):
                results['PIPELINE_STATUS_COLUMNS'].append('SUCCESS')
        else: results['PIPELINE_STATUS_COLUMNS'].append('FAIL')
            
    
    else: #no sign participant passed, assume failure for all datatypes
        results['PIPELINE_STATUS_COLUMNS'].append('FAIL')
        
    return results


def check_bold(subject_dir):
    
    
    subject_id = subject_dir.split('/')[-1].split('-')[-1]
    session_id = [x for x in subject_dir.split('/') if 'ses' in x][0].split('-')[-1]
    
    #read MRIQC pipeline output log
    output_log = subject_dir + '/mriqc_out_' + str(subject_id) + '.log'

    f = open(output_log, 'r')
    
    if "Participant level finished successfully." in f.read(): 
        acq_bold = subject_dir + '/' + subject_id + '_ses-' + session_id + '*_task-rest_run-*_bold*'
    
        if glob.glob(acq_bold):
                return 'SUCCESS'
        else: return 'FAIL'

    else: #no sign participant passed, assume failure for all datatypes
        return 'FAIL'
         

tracker_configs = {
    "pipeline_complete": eval_mriqc,
    
    "Stage_": {
            "MRIQC_BOLD": check_bold
            }
}

