import os
# Heuristics created by Vincent for PPMI dataset T1/T2/DTI images.
# 22th Mar. 2022

def create_key(template, outtype=('nii.gz',), annotation_classes=None):
    if template is None or not template:
        raise ValueError('Template must be a valid format string')
    return template, outtype, annotation_classes

def infotodict(seqinfo):
    """Heuristic evaluator for determining which runs belong where
    allowed template fields - follow python string module:
    item: index within category
    subject: participant id
    seqitem: run number during scanning
    subindex: sub index within group
    """
    t1w = create_key('sub-{subject}/{session}/anat/sub-{subject}_run-{item:01d}_T1w')
    t2w = create_key('sub-{subject}/{session}/anat/sub-{subject}_run-{item:01d}_T2w')
    dwi = create_key('sub-{subject}/{session}/dwi/sub-{subject}_run-{item:01d}_dwi')
    #dwi_fieldmap = create_key('sub-{subject}/{session}/fmap/sub-{subject}_acq-dwi_run-{item:01d}_fieldmap')
    #rest = create_key('sub-{subject}/{session}/func/sub-{subject}_task-rest_run-{item:01d}_bold')
    #rest_fieldmap = create_key('sub-{subject}/{session}/fmap/sub-{subject}_task-rest_acq-bold_run-{item:01d}_fieldmap')
    #swi = create_key('sub-{subject}/{session}/swi/sub-{subject}_run-{item:01d}_swi')
    #info = {t1w: [], t2w: [], dwi: [], rest: [],  dwi_fieldmap: [], rest_fieldmap: [], swi: []}
    info = {t1w: []}
    
    data = create_key('run{item:03d}')
    last_run = len(seqinfo)
    for idx, s in enumerate(seqinfo):
        print(s) 
        if s.is_derived == False:
            if ('MPRAGE' in s.series_description) or ('T1' in s.series_description):
                print("****** T1 ******")
                info[t1w].append(s.series_id)
            if 'T2' in s.series_description:
                print("****** T2 ******")
                info[t2w].append(s.series_id)
            if 'DTI' in s.series_description:
                print("****** DWI ******")
                info[dwi].append(s.series_id)
        #print(s.is_motion_corrected)
        #print('BOLD: ', 'BOLD' in s.protocol_name)
        #print('bold: ', 'bold' in s.protocol_name)
        #print('rest: ', 'rest' in s.protocol_name)
        #print('Rest: ', 'Rest' in s.protocol_name)
        #print('motion'': ', s.is_motion_corrected=='False')
        #print('motion: ', s.is_motion_corrected==False)
        #print('final: ', ((('BOLD' in s.protocol_name) or ('bold' in s.protocol_name)) and (('rest' in s.protocol_name) or ('Rest' in s.protocol_name)) and (s.is_motion_corrected==False)))
        #if ((('BOLD' in s.protocol_name) or ('bold' in s.protocol_name)) and (('rest' in s.protocol_name) or ('Rest' in s.protocol_name)) and (s.is_motion_corrected==False)):
        #    print('this is bold: ', s.is_motion_corrected)
        #    if 'gre_field_mapping' in s.protocol_name:
        #        print("****** rs-fMRI filedmap ******")
        #        info[rest_fieldmap].append(s.series_id)
        #    else:
        #        print("****** rs-fMRI ******")
        #        info[rest].append(s.series_id)
        #if ('swi' in s.protocol_name or 'SWI' in s.protocol_name):
        #    print("****** SWI ******")
        #    info[swi].append(s.series_id) 
    return info
