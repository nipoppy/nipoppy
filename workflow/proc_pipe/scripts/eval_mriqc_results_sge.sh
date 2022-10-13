#!/bin/bash
#
#$ -cwd
#$ -e /home/bic/inesgp/mriqc_qpn_err.log
#$ -l h_vmem=60G
#$ -M inesgp99@gmail.com
#$ -m bae
#$ -q origami.q
#$ -t 1-2

#input_dir=$1 #/data/origami/ines
#results_file=$2


while getopts i:r:p: flag
do
    case "${flag}" in
        i) input_dir=${OPTARG};;
        r) results_file=${OPTARG};;
        p) subject_list=${OPTARG};;
    esac
done

index=$((${SGE_TASK_ID}+1))

subject_id=`sed -n "${index}p" $subject_list`
for line in ${subject_line[@]}; do
	subject_id=$line
		
	break
done

subject_id=`echo $subject_id | sed 's/^ *$//g'`
output_log=$input_dir/mriqc_out_$SGE_TASK_ID.log

acq_t1w="$input_dir/${subject_id}_ses-01_acq-NM_run-1_T1w.html"
t1w="$input_dir/${subject_id}_ses-01_run-1_T1w.html"
bold="$input_dir/${subject_id}_ses-01_task-rest_run-1_bold.html"


if grep "Participant level finished successfully." $output_log
then

	if test -f $acq_t1w
	then
		acq_result="Success"
	else
		acq_result="Fail"
	fi

	if test -f $t1w
	then
		t1w_result="Success"
	else
		t1w_result="Fail"
	fi
	
	if test -f $bold
	then
		bold_result="Success"
	else
		bold_result="Fail"
	fi

        echo "$subject_id, $acq_result, $t1w_result, $bold_result" >> $results_file
else
        echo "$subject_id, Fail, Fail, Fail" >> $results_file 

fi

