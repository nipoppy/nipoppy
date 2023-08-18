#!/bin/bash
#SBATCH --mem=8G
#SBATCH --time=1:30:00

echo "========== START TIME =========="
echo `date`

if [ ! -z $SLURM_JOB_ID ]
then
    echo "========== JOB SETTINGS =========="
    TIMELIMIT="$(squeue -j ${SLURM_JOB_ID} -h --Format TimeLimit | xargs)"
    echo "SLURM_JOB_ID:        $SLURM_JOB_ID"
    echo "SLURM_MEM_PER_NODE:  $SLURM_MEM_PER_NODE"
    echo "TIMELIMIT:           $TIMELIMIT"
    echo "SLURM_ARRAY_TASK_ID: $SLURM_ARRAY_TASK_ID"
    echo "WORKING DIRECTORY:   `pwd`"
fi

echo "========== SETTINGS =========="

if [ $# -ne 2 ]
then
    echo "Usage: $0 FPATH_ZIP DPATH_DEST"
    exit 1
fi

FPATH_ZIP="$1"
DPATH_DEST="$2"

echo "FPATH_ZIP:             $FPATH_ZIP"
echo "DPATH_DEST:            $DPATH_DEST"

# append suffix to filepath
if [[ ! -z $SLURM_ARRAY_TASK_ID && $SLURM_ARRAY_TASK_ID -gt 0 ]]
then
    SUFFIX=$SLURM_ARRAY_TASK_ID
    FPATH_ZIP="${FPATH_ZIP%.*}$SUFFIX.${FPATH_ZIP##*.}"

    echo "SUFFIX:                $SUFFIX"
    echo "FPATH_ZIP with suffix: $FPATH_ZIP"
fi

echo "========== MAIN =========="

# input validation
if [ ! -f $FPATH_ZIP ]
then
    echo "[ERROR] File not found: $FPATH_ZIP"
    exit 2
fi

# create destination directory if needed
if [ ! -d $DPATH_DEST ]
then
    echo "[INFO] Creating directory $DPATH_DEST since it does not exist"
    mkdir -p $DPATH_DEST
fi

# -q: quiet
# -o: overwrite
# -d: output directory
UNZIP_COMMAND="unzip -qo $FPATH_ZIP -d $DPATH_DEST " # add -o to overwrite
echo "[RUN] $UNZIP_COMMAND"
eval "$UNZIP_COMMAND"

echo "========== END TIME =========="
echo `date`
