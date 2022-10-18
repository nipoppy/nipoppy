import os
# HeuDiConv heuristics
# Test shutil 

# Based on: https://github.com/nipy/heudiconv/blob/master/heudiconv/heuristics/example.py
POPULATE_INTENDED_FOR_OPTS = {
        'matching_parameters': ['ModalityAcquisitionLabel'],
        'criterion': 'Closest'
}

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

    #---------anat-----------#
    T1w = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_run-{item:01d}_T1w')
    T1wTFE = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_acq-TFE_run-{item:01d}_T1w')
    
    # Other T1w prefixed acq
    T1wSPIR = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_acq-SPIR_run-{item:01d}_T1w')
    T1wTFEGD  = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_acq-TFE_ce-GD_run-{item:01d}_T1w')
    
    T1wMPRCOR = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_acq-MPRCOR_run-{item:01d}_T1w')
    T1wMPRTRANS = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_acq-MPRTRANS_run-{item:01d}_T1w')

    T2w = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_run-{item:01d}_T2w')

    PDw = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_run-{item:01d}_PDw')

    FLAIR = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_run-{item:01d}_FLAIR')
    FLAIRCOR = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_acq-COR_run-{item:01d}_FLAIR')
    FLAIRTRANS = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_acq-TRANS_run-{item:01d}_FLAIR')

    #---------dwi-----------#
    dkiFOR = create_key('sub-{subject}/{session}/dwi/sub-{subject}_{session}_acq-DKIFOR_run-{item:01d}_dwi')
    dkiREV = create_key('sub-{subject}/{session}/dwi/sub-{subject}_{session}_acq-DKIREV_run-{item:01d}_dwi')
    
    #---------fmap-----------#
    #fmapAX = create_key('sub-{subject}/{session}/fmap/sub-{subject}_{session}_acq-bold_run-{item:01d}_epi')
    fmapAX = create_key('sub-{subject}/{session}/fmap/sub-{subject}_{session}_acq-bold_dir-{item:01d}_run-{item:01d}_epi.json')

    #---------perf-----------#
    asl = create_key('sub-{subject}/{session}/perf/sub-{subject}_{session}_run-{item:01d}_asl')
    fmapM0 = create_key('sub-{subject}/{session}/perf/sub-{subject}_{session}_acq-SENSE_run-{item:01d}_m0scan')

    #---------func-----------#
    bold = create_key('sub-{subject}/{session}/func/sub-{subject}_{session}_task-rest_run-{item:01d}_bold')
    boldMB = create_key('sub-{subject}/{session}/func/sub-{subject}_{session}_task-rest_acq-multiband_run-{item:01d}_bold')

    # info dict to be populated
    info = {
            T1w: [], T1wTFE: [], T1wSPIR: [], T1wTFEGD: [], T1wMPRCOR: [], T1wMPRTRANS: [], 
            T2w: [], FLAIR: [], FLAIRCOR: [], FLAIRTRANS: [], PDw: [], 
            dkiFOR: [], dkiREV: [], 
            bold: [], boldMB: [], 
            fmapAX: [], fmapM0: [],
            asl: []
           }
    
    ##########################################################################################################
    ## This is typically what you will have to change based on your scanner protocols
    ## Use heudiconv stage_1 output file:dicominfo.tsv from all subjects to identify all possible protocol names
    ##########################################################################################################

    keys_protocols_dict = {
        T1w: ['Sag_3D_MPRAGE'],
        T1wTFE: ['sT1W_3D_TFE_MPRAGE'],
        T1wSPIR: ["T1W_3D_SPIR"],
        T1wTFEGD: ["sT1W_3D_TFE_32ch_GD"],
        T1wMPRCOR:["MPR COR"],
        T1wMPRTRANS:["MPR TRANS"],

        T2w:["3D_Brain_VIEW_T2"],
        FLAIR:["3D_Brain_VIEW_FLAIR_SHC"],
        FLAIRCOR:["V3D_Brain_VIEW_FLAIR_OCOR"],
        FLAIRTRANS:["V3D_Brain_VIEW_FLAIR_TRANS"],
        PDw:["PDW_TSE_Tra","PDW_TSE_Tra"],

        dkiFOR:['DKI_uniform_distribution_FOR'],
        dkiREV:['DKI_uniform_distribution_rev'],

        asl: ["SOURCE - ASL SENSE_NEW"],
        fmapM0: ["M0 meting SENSE"],

        "boldMB":['MB2_sample fmri protocol'],        

        fmapAX: ['Axial field mapping'],
        
    }

    ##########################################################################################################

    data = create_key('run{item:03d}')
    last_run = len(seqinfo)
    for idx, s in enumerate(seqinfo):
        print(s)
        for key,protocols in keys_protocols_dict.items():
            print(f"key: {key}, protocols: {protocols}")
            for ptcl in protocols:
                if (ptcl in s.protocol_name):   
                    if key == "boldMB":
                        if (s.dim3 == 16000):                            
                            info[boldMB].append(s.series_id)

                    else:
                        info[key].append(s.series_id)
                
    return info
