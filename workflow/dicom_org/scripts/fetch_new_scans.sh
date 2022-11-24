#!/bin/bash

if [ "$#" -ne 2 ]; then
   echo "Provide path to dataset_dicom_dir and new_subject_list"
   exit 1
fi

DATASET_DICOM_DIR=$1
SUBJECT_LIST=$2

SUBJECT_LIST_DIR=`dirname "$SUBJECT_LIST"`
LOG_FILE=$SUBJECT_LIST_DIR/fetch_dicom.log
touch $LOG_FILE
chmod 755 $LOG_FILE

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
      echo "$i, dicom_missing, tar_false" >> $LOG_FILE
   else
      matches=`echo $DICOM_NAME | tr ' ' '\n'`
      n_matches=`echo $matches | wc -l`
      echo "number of dicom matches: $n_matches for subject $i"
      echo ""
      echo "*****************************************************"
      # Need to explicitly claim based on BIC's policy (Sept 2022)
      find_mri -claim -noconfir $DICOM_NAME 
      echo "*****************************************************"
      echo ""

      tar="false"
      for match in $matches; do
	      matched_subject_dir=`basename "$match"`
	      echo "Matched subject dir: $matched_subject_dir"
         if [ ! -d ${DATASET_DICOM_DIR}/ses-01/${matched_subject_dir} ] && [ ! -d ${DATASET_DICOM_DIR}/ses-02/${matched_subject_dir} ] && [ ! -d ${DATASET_DICOM_DIR}/ses-unknown/${matched_subject_dir} ]; then
            cp -r ${match} ${DATASET_DICOM_DIR}/
            chmod -R 775 ${DATASET_DICOM_DIR}/${matched_subject_dir}

	         # check if it's a tar file
            echo "Checking if the matched subject dir is a tar.gz file"
            if tar tf "${DATASET_DICOM_DIR}/${matched_subject_dir}" 2> /dev/null 1>&2; then 
               tar="true"
               echo "untarring $matched_subject_dir"
               subject_dir=`echo $matched_subject_dir | cut -d "." -f1`
               
               mkdir ${DATASET_DICOM_DIR}/{${subject_dir},tmp}
               chmod 775 ${DATASET_DICOM_DIR}/${subject_dir}
               chmod 775 ${DATASET_DICOM_DIR}/tmp

               tar xzf ${DATASET_DICOM_DIR}/${matched_subject_dir} --directory ${DATASET_DICOM_DIR}/tmp

               echo "Moving dcm files to the top-level subject dir"
               mv `find ${DATASET_DICOM_DIR}/tmp/ -name MR*` ${DATASET_DICOM_DIR}/${subject_dir}/
               echo "Cleaning up tar and tmp dirs"
               rm -rf ${DATASET_DICOM_DIR}/tmp ${DATASET_DICOM_DIR}/${matched_subject_dir} 
            fi
         else
            echo "${match} already exists within ${DATASET_DICOM_DIR}" 
         fi
      done
      echo "$i, dicom_matches_$n_matches, tar_${tar}" >> $LOG_FILE
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
echo "Check log here: $LOG_FILE"
echo ""
echo "Dicom transfer complete"