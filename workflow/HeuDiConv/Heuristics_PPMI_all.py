# -*- coding: utf-8 -*-
"""
Heuristics created by Vincent for PPMI dataset T1/T2/DTI images.
created @ 22th Mar. 2022
merged Ross's heuristics @ 30th Mar. 2022
"""
import os
import logging

lgr = logging.getLogger(__name__)
scaninfo_suffix = '.json'

# scanning protocol details
# converted
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

# converted
T2W_SERIES = [
    # single echo only
    't2_tse_tra',
    't2 cor',
    'T2 COR',
    'T2W_TSE',
    'AX T2',
    'AX T2 AC-PC LINE ENTIRE BRAIN',
    'AX T2 AC-PC line Entire Brain',
    'Ax T2 Fse thin ac-pc',
    # mixed single / dual-echo
    'AXIAL FSE T2 FS',
    'T2',
    '*AX FSE T2', # added from livingpark
    'AXIAL  T2  FSE',
    '_AX_FSE_T2',
    ' 3-pl_T2__FGRE'
]

# converted as T2 with acq-GREMT, according to study design
MT_SERIES = [
    ## T2 MT added by Vincent 
    '2D GRE - MT',
    '2D GRE MT',
    '2D GRE-MT',
    '2D GRE-MT_RPT2',
    '2D GRE-NM',
    '2D GRE-NM_MT',
    '2D_GRE-MT',
    'AX GRE -MT',
    'AXIAL 2D GRE-MT',
    'LOWER 2D GRE MT',
    '2D GRE MT MTC-NO', # added from living park
    'NM-MT', # added from all T1 PPMI
    '2D_GRE-NM',
    '2D_GRE_-_MT',
    'SAG_3D_SPGR',
    'MPRAGE_w__GRAPPA_2',
    'T1_AXIAL',
    'sag',
    'SAG_T1_3D_MPRAGE',
    'AXIAL_T1_3D_MPRAGE',
    '2D_GRE_MT',
    'AXIAL_2D_GRE-MT',
    '2DGRE-MT',
    '2D_GRE-MT_RPT2', 
    'AX_GRE_-MT',
    '2D_GRE_MT_MTC-NO',
    'AX_2D_GRE-MT',
    '2D_GRE-NM_MT',
    'AX_T2_GRE_MT',
    'LOWER_2D_GRE_MT',
]

# converted
T2_STAR_SERIES = [
    'AXIAL_T2_STAR'
]

# converted
PDT2_SERIES = [
    'AX DE TSE',
    'AX DUAL_TSE',
    'DUAL_TSE',
    'sT2W/PD_TSE',
    'Axial PD-T2-FS TSE',
    'Axial PD-T2 TSE',
    'Axial PD-T2 TSE FS',
    'AXIAL PD-T2 TSE FS',
    'AX PD + T2',
    'PD-T2 DUAL AXIAL TSE',
    'Axial PD-T2 TSE_AC/PC line',
    'Axial PD-T2 TSE_AC PC line',
    'Ax PD /T2',
    'AXIAL PD+T2 TSE',
    'AX T2 DE',
    't2 weighted double echo',
    'Axial_PD_T2', ## Added from all T1 PPMI version
    'AX_T2',
    'Axial_PD-T2_TSE_FS',
    'AX_PD_+_T2',
    'Ax_PD__T2',
    'Axial_PD-T2_TSE',
    'AX_DUAL_TSE',
]

# converted
FLAIR_SERIES = [
    # FLAIR (no weighting specified)
    'FLAIR_LongTR AX',
    'FLAIR_LongTR SENSE',
    'AX FLAIR',
    'AXIAL FLAIR',
    'FLAIR_longTR',
    'FLAIR AXIAL',
    'ax flair',
    'Cor FLAIR TI_2800ms',
    'FLAIR',
    # T2 FLAIR
    'AX T2 FLAIR',
    'T2  AXIAL FLAIR',
    'Ax T2 FLAIR  ang to ac-pc',
    'T2W_FLAIR',
    'AX FLAIR T2',
    'AX T2 FLAIR 5/1',
    'Ax T2 FLAIR',
    't2_tirm_tra_dark-fluid_',
    't2_tirm_tra_dark-fluid NO BLADE',
    # T1 FLAIR -- should these be here?
    'Ax T1 FLAIR',
    # added by Vincent
    '3D T2  SPC FLAIR C9C1HN007',
    '3D T2 FLAIR',
    '3D T2 FLAIR_ND',
    '3D T2 FLAIR_SAGITAL',
    '3D T2 FLAIR_ti1650',
    '3D T2 FLAIR_ti1650_ND',
    '3D_Brain_VIEW_FLAIR_SAG',
    '3D_T2_FLAIR',
    '3D_T2_FLAIR_SAG INVICCRO T2 FLAIR',
    'SAG 3D FLAIR',
    'SAG CUBE FLAIR',
    'Sag 3D T2 FLAIR',
    'SAG 3D T2 FLAIR_',  # added from livingpark
    'AX_T2_FLAIR', # added from all T1
    'Sag_MPRAGE_GRAPPA_ND',
    'FLAIR_LongTR_AX',
    'MPRAGE_GRAPPA_ND',
    'Ax_T2_FLAIR',
    'SAG_MPRAGE_GRAPPA_ND',
    'AX_FLAIR',
    '3D_SAG_T1_MPRAGE_ND',
]

# converted
DTI_SERIES = [
    'DTI_gated',
    'DTI_non_gated',
    'DTI_pulse gated_AC/PC line',
    'REPEAT_DTI_GATED',
    'DTI_NONGATED',
    'REPEAT_DTI_NONGATED',
    'TRIGGERED DTI',
    'DTI_NON gated',
    'DTI_ non_gated',
    'DTI_non gated Repeat',
    'DTI_NON-GATED',
    'REPEAT_DTI_NON-GATED',
    'DTI_none_gated',
    'DTI_non gated',
    'Repeat DTI_non gated',
    'REPEAT_NON_GATED',
    'DTI',
    'REPEAT_DTI_ NON GATED',
    'REPEAT_DTI_NON GATED',
    'DTI_NON GATED',
    'DTI Sequence',
    'DTI_ NON gated REPEAT',
    'DTI_ non gated',
    'DTI_GATED',
    'DTI_NON gated REPEAT',
    'DTI_NON_GATED',
    'DTI_Non Gated',
    'DTI_Non gated',
    'DTI_Non gated Repeat',
    'DTI_Non-gated',
    'DTI_UNgated',
    'DTI_UNgated#2',
    'DTI_gated AC-PC LINE',
    'DTI_gated#1',
    'DTI_gated#2',
    'DTI_gated_ADC',
    'DTI_gated_FA',
    'DTI_gated_TRACEW',
    'DTI_non gated repeat',
    'DTI_pulse gated_AC PC line',
    'DTI_ungated',
    'REPEAT DTI_NON GATED',
    'REPEAT DTI_NON gated',
    'REPEAT_NON DTI_GATED',
    'Repeat DTI Sequence',
    ## added by Vincent
    '2D DTI EPI FAT SHIFT LEFT',
    '2D DTI EPI FAT SHIFT RIGHT',
    'AX DTI   L - R',
    'AX DTI   L - R  (ROTATE AXIAL FOV 45 DEGREES)',
    'AX DTI   R - L',
    'AX DTI LR',
    'AX DTI RL',
    'Ax DTI',
    'Axial DTI FREQ A_P',
    'Axial DTI L>R',
    'Axial DTI R>L',
    'DTI Sequence REPEAT',
    'DTI_ LR',
    'DTI_ RL',
    'DTI_30dir L-R',
    'DTI_30dir R-L',
    'DTI_LR',
    'DTI_LR_split_1',
    'DTI_N0N GATED',
    'DTI_NON-gated',
    'DTI_RL',
    'DTI_RL_split_1',
    'DTI_gated NON',
    'DTI_non gated Repeated',
    'DTI_non-gated',
    'DTI_none gated',
    'NON DTI_gated'
]

#by now DTI derivatives are not converted
DTI_derived_SERIES = [
    'DTI Sequence_ADC',    # derivate?
    'DTI Sequence_FA',     # derivate?
    'DTI Sequence_TRACEW', # derivate?
    'DTI_ADC',              # derivate?
    'DTI_EXP',              # derivate?
    'DTI_FA',               # derivate?
    'DTI_TRACEW',                   # derivate?
    'DTI_gated AC-PC LINE_FA',      # derivate?
    'DTI_gated AC-PC LINE_TRACEW'  # derivate?
]

# not converted by now
BOLD_SERIES = [
    'ep2d_RESTING_STATE',
    'ep2d_bold_rest',
    'ep2d_diff_LR',
    'ep2d_diff_RL'
    'rsfMRI_LR', # added from livingpark
    'rsfMRI_RL',
    'BOLD_RS ACPC_LINE',
    'repeat_BOLD_RS ACPC_LINE', 
]

# not converted by now
UN_classified_SERIES = [
    'B0rf Map',
    'Field_mapping',
    'GRE B0',
    'localizer',
    'MPRAGE_64channel_p2', # Added from PPMI all T1 version
    'COR',
    'MPRAGE_ASO',
    'B0rf_Map',
    '3_plane',
    'GRE_B0',
    'MR',
    'Transverse',
    'TRA',
    'MPRAGE_Phantom_GRAPPA2',
    'Cal_Head_24',
    'SURVEY',
    '3_PLANE_LOC',
    'MIDLINE_SAG_LOC',
    ''
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
    t1w        = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_run-{item:02d}_T1w')  # noqa
    t1w_grappa = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_acq-grappa2_run-{item:02d}_T1w')  # noqa
    t1w_adni   = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_acq-adni_run-{item:02d}_T1w')  # noqa
    t2w        = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_run-{item:02d}_T2w')  # noqa
    t2MT       = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_acq-GREMT_run-{item:02d}_T2w')  # noqa
    t2starw    = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_run-{item:02d}_T2starw')  # noqa
    pdt2       = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_run-{item:02d}_MESE')  # noqa
    flair      = create_key('sub-{subject}/{session}/anat/sub-{subject}_{session}_run-{item:02d}_FLAIR')  # noqa
    dwi        = create_key('sub-{subject}/{session}/dwi/sub-{subject}_{session}_run-{item:02d}_dwi')  # noqa
    bold       = create_key('sub-{subject}/{session}/func/sub-{subject}_{session}_task-rest_run-{item:02d}_bold')  # noqa
    
    #swi = create_key('sub-{subject}/{session}/swi/sub-{subject}_run-{item:01d}_swi')
    info = {t1w: [], t1w_grappa: [], t1w_adni: [], t2w: [], t2MT: [],
            t2starw: [], pdt2: [], flair: [], dwi: [], bold: []}
    revlookup = {}

    for idx, s in enumerate(seqinfo):
        revlookup[s.series_id] = s.series_description
        print(s)
        # the straightforward scan series
        if s.series_description in T1W_SERIES:# T1
            info[t1w].append(s.series_id)
        elif s.series_description in T2W_SERIES:# T2
            info[t2w].append(s.series_id)
        elif s.series_description in MT_SERIES:# T2star
            info[t2MT].append(s.series_id)  
        elif s.series_description in T2_STAR_SERIES:# T2star
            info[t2starw].append(s.series_id)          
        elif s.series_description in PDT2_SERIES:# PDT2
            info[pdt2].append(s.series_id)
        elif s.series_description in FLAIR_SERIES:# FLAIR
            info[flair].append(s.series_id)
        elif s.series_description in DTI_SERIES:# DWI, all derivatives are not included
            info[dwi].append(s.series_id)
        elif s.series_description in BOLD_SERIES:# BOLD
            info[bold].append(s.series_id)
        # if we don't match _anything_ then we want to know!
        else:
            lgr.warning('Skipping unrecognized series description: {}'.format(s.series_description))

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

## Taken from Ross code
# def custom_callable(*args):
#     """
#     Called at the end of `heudiconv.convert.convert()` to perform clean-up

#     Checks to see if multiple "clean" output files were generated by
#     ``heudiconv``. If so, assumes that this was because they had different echo
#     times and tries to rename them and embed metadata from the relevant dicom
#     files. This only needs to be done because the PPMI dicoms are a hot mess
#     (cf. all the lists above with different series descriptions).
#     """

#     import glob
#     import re
#     import pydicom as dcm
#     import nibabel as nib
#     import numpy as np
#     from heudiconv.cli.run import get_parser
#     from heudiconv.dicoms import embed_metadata_from_dicoms
#     from heudiconv.utils import (
#         load_json,
#         TempDirs,
#         treat_infofile,
#         set_readonly
#     )

#     # unpack inputs and get command line arguments (again)
#     # there's gotta be a better way to do this, but c'est la vie
#     prefix, outtypes, item_dicoms = args[:3]
#     outtype = outtypes[0]
#     opts = get_parser().parse_args()

#     # if you don't want BIDS format then you're going to have to rename outputs
#     # on your own!
#     if not opts.bids:
#         return

#     # do a crappy job of checking if multiple output files were generated
#     # if we're only seeing one file, we're good to go
#     # otherwise, we need to do some fun re-naming...
#     res_files = glob.glob(prefix + '[1-9].' + outtype)
#     if len(res_files) < 2:
#         return

#     # there are few a sequences with some weird stuff that causes >2
#     # files to be generated, some of which are two-dimensional (one slice)
#     # we don't want that because that's nonsense, so let's design a check
#     # for 2D files and just remove them
#     for fname in res_files:
#         if len([f for f in nib.load(fname).shape if f > 1]) < 3:
#             os.remove(fname)
#             os.remove(fname.replace(outtype, 'json'))
#     res_files = [fname for fname in res_files if os.path.exists(fname)]
#     bids_pairs = [(f, f.replace(outtype, 'json')) for f in res_files]

#     # if there's only one file remaining don't add a needless 'echo' key
#     # just rename the file and be done with it
#     if len(bids_pairs) == 1:
#         safe_movefile(bids_pairs[0][0], prefix + '.' + outtype)
#         safe_movefile(bids_pairs[0][1], prefix + scaninfo_suffix)
#         return

#     # usually, at least two remaining files will exist
#     # the main reason this happens with PPMI data is dual-echo sequences
#     # look in the json files for EchoTime and generate a key based on that
#     echonums = [load_json(json).get('EchoTime') for (_, json) in bids_pairs]
#     if all([f is None for f in echonums]):
#         return
#     echonums = np.argsort(echonums) + 1

#     for echo, (nifti, json) in zip(echonums, bids_pairs):
#         # create new prefix with echo specifier
#         # this isn't *technically* BIDS compliant, yet, but we're making due...
#         split = re.search(r'run-(\d+)_', prefix).end()
#         new_prefix = (prefix[:split]
#                       + 'echo-%d_' % echo
#                       + prefix[split:])
#         outname, scaninfo = (new_prefix + '.' + outtype,
#                              new_prefix + scaninfo_suffix)

#         # safely move files to new name
#         safe_movefile(nifti, outname, overwrite=False)
#         safe_movefile(json, scaninfo, overwrite=False)

#         # embed metadata from relevant dicoms (i.e., with same echo number)
#         dicoms = [f for f in item_dicoms if
#                   isclose(float(dcm.read_file(f, force=True).EchoTime) / 1000,
#                           load_json(scaninfo).get('EchoTime'))]
#         prov_file = prefix + '_prov.ttl' if opts.with_prov else None
#         embed_metadata_from_dicoms(opts.bids, dicoms,
#                                    outname, new_prefix + '.json',
#                                    prov_file, scaninfo, TempDirs(),
#                                    opts.with_prov, opts.minmeta)

#         # perform the bits of heudiconv.convert.convert that were never called
#         if scaninfo and os.path.exists(scaninfo):
#             lgr.info("Post-treating %s file", scaninfo)
#             treat_infofile(scaninfo)
#         if outname and os.path.exists(outname):
#             set_readonly(outname)

#         # huzzah! great success if you've reached this point


# def isclose(a, b, rel_tol=1e-06, abs_tol=0.0):
#     """
#     Determine whether two floating point numbers are close in value.

#     Literally just math.isclose() from Python >3.5 as defined in PEP 485

#     Parameters
#     ----------
#     a, b, : float
#         Floats to compare
#     rel_tol : float
#        Maximum difference for being considered "close", relative to the
#        magnitude of the input values
#     abs_tol : float
#        Maximum difference for being considered "close", regardless of the
#        magnitude of the input values

#     Returns
#     -------
#     bool
#         True if `a` is close in value to `b`, and False otherwise.

#     For the values to be considered close, the difference between them must be
#     smaller than at least one of the tolerances.
#     """

#     return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


# def safe_movefile(src, dest, overwrite=False):
#     """
#     Safely move `source` to `dest`, avoiding overwriting unless `overwrite`

#     Uses `heudiconv.utils.safe_copyfile` before calling `os.remove` on `src`

#     Parameters
#     ----------
#     src : str
#         Path to source file; will be removed
#     dest : str
#         Path to dest file; should not exist
#     overwrite : bool
#         Whether to overwrite destination file, if it exists
#     """

#     from heudiconv.utils import safe_copyfile

#     try:
#         safe_copyfile(src, dest, overwrite)
#         os.remove(src)
#     except RuntimeError:
#         lgr.warning('Tried moving %s to %s but %s ' % (src, dest, dest)
#                     + 'already exists?! Check your outputs to make sure they '
#                     + 'look okay...')
