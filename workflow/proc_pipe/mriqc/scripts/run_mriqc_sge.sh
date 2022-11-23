#!/bin/bash
#
#$ -cwd
#$ -e ERROR LOG FILE 
#$ -l h_vmem=60G
#$ -M EMAIL ADDRESS
#$ -m bae
#$ -q origami.q
#$ -t 120-162

while getopts d:r:p:c: flag
do
    case "${flag}" in
        c) container=${OPTARG};;
        d) data_dir=${OPTARG};;
        r) results_dir=${OPTARG};;
        p) subject_list=${OPTARG};;
    esac
done

index=$((${SGE_TASK_ID}+1))
subject_id=`sed -n "${index}p" $subject_list`
#new lines to extract subject from participant tsv file
subject_id=(${subject_id// / })
subject_id=${subject_id[0]}
echo $subject_id >> $results_dir/mriqc_out_$SGE_TASK_ID.log

singularity run --cleanenv -B ${data_dir}:/data:ro -B ${results_dir}:/out $container --no-sub /data /out participant --participant-label $subject_id >> ${results_dir}/mriqc_out_$SGE_TASK_ID.log

