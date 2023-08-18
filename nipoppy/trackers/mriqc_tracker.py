import sys
import json
import glob


#/scratch/qpn/sub-01/

def eval_mriqc(subject_dir, session_id, run_id=None):
    
       
    #get subject id from directory
    subject_id = subject_dir.split('/')[-1].split('-')[-1]


    #read MRIQC pipeline output log
    output_log = subject_dir + '/mriqc_out_' + str(subject_id) + '.log'
    f = open(output_log, 'r')

    #set up dictionary to return
    results = {'participant_id': [subject_id], 'PIPELINE_STATUS_COLUMNS': []} 
    
        
    #check if participant successfully passed MRIQC pipeline
    if "Participant level finished successfully." in f.read(): 
        
        #create path string
        acq_T1w = subject_dir + '/' + str(subject_id) + '_ses-' + str(session_id) + '*_run-*_T1w*'
        
        #check if string is an existing path
        if glob.glob(acq_T1w):
                results['PIPELINE_STATUS_COLUMNS'].append('SUCCESS')
        else: results['PIPELINE_STATUS_COLUMNS'].append('FAIL')
            
    
    else: #no sign participant passed, assume failure for all datatypes
        results['PIPELINE_STATUS_COLUMNS'].append('FAIL')
        
    return results


def check_bold(subject_dir, session_id, run_id=None):
    
    #get subject id from directory
    subject_id = subject_dir.split('/')[-1].split('-')[-1]

    
    #read MRIQC pipeline output log
    output_log = subject_dir + '/mriqc_out_' + str(subject_id) + '.log'

    f = open(output_log, 'r')
    
    #check if participant successfully passed MRIQC pipeline
    if "Participant level finished successfully." in f.read(): 
        
        #create path string
        acq_bold = subject_dir + '/' + subject_id + '_ses-' + session_id + '*_task-rest_run-*_bold*'
    
    	#check if string is existing path
        if glob.glob(acq_bold):
                return 'SUCCESS'
        else: return 'FAIL'

    else: #no sign participant passed, assume failure for all datatypes
        return 'FAIL'
         

#eval_mriqc returns participant_id and pass/fail while check_bold only returns pass/fail
tracker_configs = {
    "pipeline_complete": eval_mriqc,
    
    "STAGE_": {
            "MRIQC_BOLD": check_bold
            }
}

