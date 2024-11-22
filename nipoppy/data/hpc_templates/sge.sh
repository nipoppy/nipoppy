#!/bin/bash
#$ -N {{job_name}}
#$ -wd {{working_directory}}
{%- if cores %}
#$ -pe all.pe {{cores}}
{%- endif %}
{%- if memory_max %}
#$ -l h_vmem={{memory_max}}
{%- endif %}
{%- if run_time_max %}
#$ -l h_rt={{ '%02d:%02d:%02d' % (run_time_max // 60, run_time_max % 60, 0) }}
{%- endif %}
{%- if account %}
#$ -q {{account}}
{%- endif %}
#$ -t 1-{{num_tasks}}   # Specifies the array job range
#$ -tc 100              # Limits the maximum number of tasks running at the same time
#$ -o time_$TASK_ID.out # Separate output file for each task
#$ -e error_$TASK_ID.out # Separate error file for each task

{{command}}

