#!/bin/bash
#
#$ -cwd
#$ -e /home/bic/inesgp/mriqc_qpn_err.log
#$ -l h_vmem=60G
#$ -M inesgp99@gmail.com
#$ -m bae
#$ -q origami.q
#$ -t 120-162

#umask u=rwx,g=rwx,o=rx
#echo `which mkdir`

while getopts i:r:p: flag
do
    case "${flag}" in
        d) data_dir=${OPTARG};;
        r) results_dir=${OPTARG};;
        p) subject_list=${OPTARG};;
    esac
done

index=$((${SGE_TASK_ID}+1))
subject_id=`sed -n "${index}p" $subject_list`
echo $subject_id >> $results_dir/mriqc_out_$SGE_TASK_ID.log

singularity run --cleanenv -B ${data_dir}:/data:ro -B ${results_dir}:/out /data/pd/qpn/proc/containers/mriqc_patch2.simg --no-sub /data /out participant --participant-label $subject_id >> ${results_dir}/mriqc_out_$SGE_TASK_ID.log

