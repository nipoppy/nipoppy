# -*- coding: utf-8 -*-
"""
Heuristics created by Vincent for PPMI dataset T1 images.
created @ 22th Mar. 2022
Ross's heuristics merged @ 30th Mar. 2022
"""
import os
import logging

lgr = logging.getLogger(__name__)
scaninfo_suffix = '.json'

# scanning protocol details
T1W_SERIES = [
    'MPRAGE 2 ADNI',
    'MPRAGE ADNI',
    'MPRAGE GRAPPA 2',
    'MPRAGE GRAPPA2',
    'MPRAGE GRAPPA2(adni)',
    'MPRAGE w/ GRAPPA',
    'MPRAGE_GRAPPA',
    'MPRAGE_GRAPPA_ADNI',
    'MPRAGE GRAPPA',
    'SAG T1 3D MPRAGE',
    'sag mprage',
    'MPRAGEadni',
    'MPRAGE GRAPPA_ND',
    '3D SAG',
    'MPRAGE T1 SAG',
    'MPRAGE SAG',
    'SAG T1 3DMPRAGE',
    'SAG T1 MPRAGE',
    'SAG 3D T1',
    'SAG MPRAGE GRAPPA2-NEW2016',
    'SAG MPRAGE GRAPPA_ND',
    'Sag MPRAGE GRAPPA',
    'AXIAL T1 3D MPRAGE',
    'SAG MPRAGE GRAPPA',
    'sT1W_3D_FFE',
    'sT1W_3D_ISO',
    'sT1W_3D_TFE',
    'sag 3D FSPGR BRAVO straight',
    'SAG T1 3D FSPGR',
    'SAG FSPGR 3D '
    'SAG 3D FSPGR BRAVO STRAIGHT',
    'SAG T1 3D FSPGR 3RD REPEAT',
    'SAG FSPGR BRAVO',
    'SAG SPGR 3D',
    'SAG 3D SPGR',
    'FSPGR 3D SAG',
    'SAG FSPGR 3D',
    'SAG 3D FSPGR BRAVO STRAIGHT',
    'SAG FSPGR 3D ',
    't1_mpr_ns_sag_p2_iso',
    'T1',
    'T1 Repeat',
    'AX T1',
    'axial spgr',
    'T1W_3D_FFE AX',
    # added by Vincent
    'AX T1 SE C+',
    '3D SAG T1 MPRAGE',
    '3D SAG T1 MPRAGE_ND',
    '3D T1',
    '3D T1 MPRAGE',
    '3D T1-weighted',
    'Accelerated Sag IR-FSPGR',
    'MPRAGE',
    'MPRAGE - Sag',
    'MPRAGE Phantom GRAPPA2',
    'MPRAGE w/ GRAPPA 2',
    'PPMI_MPRAGE_GRAPPA2',
    'SAG 3D T1 FSPGR',
    'SAG FSPGR 3D VOLUMETRIC T1',
    'Sag MPRAGE GRAPPA_ND',
    'T1-weighted, 3D VOLUMETRIC',
    'tra_T1_MPRAGE', 
    '3D T1-weighted_ND', ## added from livingpark
    '3D T1 _weighted',
    'Sagittal 3D Accelerated MPRAGE',
    'T1 REPEAT',
    'MPRAGE Repeat',
    'SAG_3D_MPRAGE',
    'T1-weighted,_3D_VOLUMETRIC', ## added from all T1 PPMI
    '3D_SAG',
    'FSPGR_3D_SAG',
    'SAG_T1_MPRAGE',
    'MPRAGE_2_ADNI',
    'MPRAGE_Repeat',
    'T1W_3D_FFE_COR',
    'SAG',
    'SAG_MPRAGE_GRAPPA2-NEW2016',
    'MPRAGE_GRAPPA_2',
    'AX_T1_SE_C+',
    '3D_Sagittal_T1',
    'Coronal',
    'MPRAGE_SENSE2',
    'sag_mprage',
    'Accelerated_Sag_IR-FSPGR',
    'SAG_SPGR',
    'MPRAGE_GRAPPA2_adni_',
    'Sag_MPRAGE_GRAPPA',
    '3D_SAG_T1_MPRAGE',
    'MPRAGE_ADNI',
    'AX_3D_FSPGR_straight_brain_lab',
    '3D_T1_MPRAGE',
    'rpt_PPMI_MPRAGE_GRAPPA2',
    'SAG_FSPGR_BRAVO',
    '3D_T1',
    'sag_3D_FSPGR_BRAVO_straight',
    'mprage',
    'AX_T1',
    'Sagittal_3D_Accelerated_MPRAGE',
    'MPRAGE_w__GRAPPA',
    'SAG_T1_3D_FSPGR',
    'SAG_3D_MPRAGE_RPT',
    'SAG_T1_SE',
    'axial_spgr',
    'SAG_T1_3D_FSPGR_3RD_REPEAT',
    'SAG_FSPGR_3D',
    'MPRAGE_SAG',
    'T1_repeat',
    'T1_SAG',
    'Sag_T1',
    'T1_REPEAT',
    'T1W_3D_FFE_AX',
    '3D_T1-weighted',
    'SAG_T1_3DMPRAGE',
    'MPRAGE_T1_SAG',
    'SAG_FSPGR_3D_VOLUMETRIC_T1',
    'SAG_3D_T1_FSPGR',
    'SAG_3D_T1',
    'T1_Repeat',
    'SAG_SPGR_3D',
    'MPRAGE_GRAPPA2', 
    'MPRAGE_-_Sag',
    'SAG_3D_FSPGR_BRAVO_STRAIGHT',
    'SAG_MPRAGE_GRAPPA',
]

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
    t1w = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_run-{item:02d}_T1w')  # noqa
    t1w_grappa = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_acq-grappa2_run-{item:02d}_T1w')  # noqa
    t1w_adni   = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_acq-adni_run-{item:02d}_T1w')  # noqa
    ####
    info = {t1w: [], t1w_grappa: [], t1w_adni: []}
    revlookup = {}

    for idx, s in enumerate(seqinfo):
        revlookup[s.series_id] = s.series_description
        print(s) 
        if s.series_description in T1W_SERIES:# T1
            info[t1w].append(s.series_id)

    # Adding "acq" for all t1w
    if len(info[t1w]) > 1:
        # copy out t1w image series ids and reset info[t1w]
        all_t1w = info[t1w].copy()
        info[t1w] = []
        for series_id in all_t1w:
            series_description = revlookup[series_id].lower()
            if series_description in ['mprage_grappa', 'sag_mprage_grappa']:
                info[t1w].append(series_id)
            elif 'adni' in series_description:
                info[t1w_adni].append(series_id)
            else:
                info[t1w_grappa].append(series_id)
    return info