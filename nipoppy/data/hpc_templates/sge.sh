#!/bin/bash
#$ -N {{job_name}}
#$ -wd {{working_directory}}
{%- if cores %}
#$ -pe impi_hy* {{cores}}
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
#$ -o time.out
#$ -e error.out

{{command}}

