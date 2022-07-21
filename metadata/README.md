# PPMI metadata

PPMI metadata, including different PPMI versions for different projects and also the meta data from QPN.

## Contents Organization

1. `ppmi` folder: the sdMRI PPMI metadata (subjects with both 3T T1 MRI and DWI);
    
    a) `participants.csv`: Participants table, including: "participant_id", "age", "sex", "group";

    b) `PPMI_3T_sdMRI_3_07_2022.csv`: PPMI collection downloading table, including: "Image Data ID","Subject","Group","Sex","Age","Visit","Modality","Description","Type","Acq Date","Format","Downloaded";

    c) `PPMI_3T_sdMRI_3_07_2022_dcminfo.csv`: PPMI dicom information from HeuDiConv run1, including:,"Image Data ID", "Visit", "Subject", "Modality", "Image Date";

    d) `PPMI_all_7_18_2022.csv`: PPMI all imaging collection (subjects with any images)downloading table, including: "Image Data ID","Subject","Group","Sex","Age","Visit","Modality","Description","Type","Acq Date","Format","Downloaded";

    e) `PPMI_all_7_18_2022_metadata.csv`: information obtained from the *.xml files acompanied the dicom images, including: "Image Data ID", "Subject", "Group", "Site", "Sex", "Visit", "Age", "weightKg", "Description", "Modality", "Weighting", "Acquisition Type", "Acq Date", "Matrix X", "Matrix Y", "Matrix Z", "Slice Thickness","studyIdentifier"

2. `livingPark` folder: the livingPark additional subjects metadata(only T1) who does not apear in the above sdMRI dataset;

    a) `PPMI_livingpark_metadata.csv`: 1st wave of additional livingPark subjects metadata obtained from the *.xml files;
    
    b) `PPMI_livingpark_dcminfo.csv`:  1st wave of additional livingPark subjects metadata obtained from HeuDiConv run1;

    c) `PPMI_livingpark2_metadata.csv`: 2nd wave of additional livingPark subjects metadata obtained from the *.xml files;

    d) `PPMI_livingpark2_dcminfo.csv`:  2nd wave of additional livingPark subjects metadata obtained from HeuDiConv run1;

    e) `MRI_info_v0.1.csv`: livingPark official MRI metadata;

    f) `livingpark_T1_7_20_2022.csv`: all subjects with T1.

3. `qpn` folder: the metadata for QPN dataset;
    
    a) `participants.csv`:  Participants table, including: "participant_id", "age", "sex", "group";

    b) `QPN_dicom_protocols.png`: QPN MRI protocols.

`proc_tracker.csv`: Progress tracker file (need unified definition of contents).

## Issues

1) livingPark is currently based on the nifti files downloaded directly from PPMI portal.
