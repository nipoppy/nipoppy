#!/bin/bash
#SBATCH --output=time_%A_%a.out            # Output filename pattern with job and array task ID
#SBATCH --job-name={{ job_name }}          # Job name
#SBATCH --account={{ account_name }}       # Account name
#SBATCH --chdir={{ working_directory }}    # Change to the specified directory
#SBATCH --get-user-env=L                   # Get user environment
#SBATCH --cpus-per-task={{ cores }}        # CPUs per task
{%- if run_time_max %}
#SBATCH --time=00:{{ run_time_max }}:00    # Max run time in mins
{%- endif %}
{%- if memory_max %}
#SBATCH --mem={{ memory_max }}G            # Max memory in GB
{%- endif %}
#SBATCH --array=0-{{ num_tasks }}%100      # Array with 100 jobs running at a time
{{ command }}
