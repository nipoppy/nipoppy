#!/bin/bash

if [ "$#" -ne 2 ]; then
   echo "Provide path to dataset_dicom_dir and new_subject_list"
   exit 1
fi

DATASET_DICOM_DIR=$1
SUBJECT_LIST=$2

SUBJECT_LIST_DIR=`dirname "$SUBJECT_LIST"`
MISSING_SUBJECT_LIST=$SUBJECT_LIST_DIR/subjects_with_missing_dicoms.txt
touch $MISSING_SUBJECT_LIST
chmod 755 $MISSING_SUBJECT_LIST

if [ ! -d "$DATASET_DICOM_DIR" ]; then
   echo "Could not find $DATASET_DICOM_DIR"
   exit 1
fi

N_SUBS=`cat $SUBJECT_LIST | wc -l`
echo "Number of new subjects: $N_SUBS"
echo ""

# find mri
for i in `cat $SUBJECT_LIST`; do
   echo ""
   echo "Searching for: $i"
   DICOM_NAME=`find_mri $i | grep "found"| grep "/data/dicom" | grep ${i} | cut -d " " -f3`
   
   if [[ "$DICOM_NAME" == "" ]]; then
      echo "No scan match found for $i in the source dir"
      echo $i >> $MISSING_SUBJECT_LIST
   else
      matches=`echo $DICOM_NAME | tr ' ' '\n'`
      n_matches=`echo $matches | wc -l`
      echo "number of dicom matches: $n_matches for subject $i"

      # Need to explicitly claim based on BIC's policy (Sept 2022)
      find_mri -claim -noconfir $DICOM_NAME 
      
      for match in $matches; do
	 scan_name=`basename "$match"`
	 echo $scan_name
         if [ ! -d ${DATASET_DICOM_DIR}/ses-01/${scan_name} ] && [ ! -d ${DATASET_DICOM_DIR}/ses-02/${scan_name} ] && [ ! -d ${DATASET_DICOM_DIR}/ses-unknown/${scan_name} ]; then
            cp -r ${match} ${DATASET_DICOM_DIR}/
            chmod -R 775 ${DATASET_DICOM_DIR}/${scan_name}

	    # check if it's a tar file
            if tar tf "${DATASET_DICOM_DIR}/${scan_name}" 2> /dev/null 1>&2; then 
               echo "untarring $scan_name"
	       subject_dir=`echo $scan_name | cut -d "." -f1`
	       
	       mkdir ${DATASET_DICOM_DIR}/{${subject_dir},tmp}
	       chmod 775 ${DATASET_DICOM_DIR}/${subject_dir}
	       chmod 775 ${DATASET_DICOM_DIR}/tmp

	       tar xzf ${DATASET_DICOM_DIR}/${scan_name} --directory ${DATASET_DICOM_DIR}/tmp
	       mv `find ${DATASET_DICOM_DIR}/tmp/ -name MR*` ${DATASET_DICOM_DIR}/${subject_dir}/
	       rm -rf ${DATASET_DICOM_DIR}/tmp ${DATASET_DICOM_DIR}/${scan_name} 
	    fi
         else
            echo "${match} exists in ${DATASET_DICOM_DIR}" 
         fi
      done
   fi
done

# reorganize based on visits (i.e. sessions for BIDS)
echo ""
echo "reorganizing scans based on visits/sessions"
mv ${DATASET_DICOM_DIR}/*MRI01* ${DATASET_DICOM_DIR}/ses-01/
mv ${DATASET_DICOM_DIR}/*MRI02* ${DATASET_DICOM_DIR}/ses-02/
mv ${DATASET_DICOM_DIR}/MNI* ${DATASET_DICOM_DIR}/ses-unknown/
mv ${DATASET_DICOM_DIR}/PD* ${DATASET_DICOM_DIR}/ses-unknown/
echo ""
echo "Check manifest subjects missing DICOMs here: $MISSING_SUBJECT_LIST"
echo "Dicom transfer complete"

