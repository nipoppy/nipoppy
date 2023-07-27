#!/bin/bash

#SBATCH --mem=8G
#SBATCH --time=2-00:00:00

# ========== SETTINGS ==========
# NOTE: fstime is set (to arbitrary value) so that checksums are the same
SQUASHFS_OPTIONS="-no-progress -keep-as-directory -all-root -processors 1 -no-duplicates -wildcards -fstime 1689602400"
COMPRESS_OPTIONS="-noD -noI -noX"

BASENAME="$(basename $0)"
EXAMPLE_CALL="$BASENAME --exclude exclude.txt --move /data output.squashfs dirA fileB"
read -r -d '' USAGE_STR << HELPTEXT
Make a SquashFS file from a list of directories and files.

This script sets file permissions 755 for directories and 644 for files,
calls mksquashfs with the following options:
    $SQUASHFS_OPTIONS
then optionally moves the files into a subdirectory inside the squashfs.

Usage: $BASENAME [-h/--help] [-e/--exclude FILE] [-m/--move PATH_INSIDE_SQUASHFS] [-d/--dry-run] [-p/--no-chmod] [-c/--no-compress] OUTPUT_FILE PATH1 [PATH2...]

where:
    OUTPUT_FILE         path to output squashfs file (must not already exist)
    PATH1 [PATH2...]    paths to directories or files to squash
    -e/--exclude        exclude files matching patterns in FILE (passed to -ef argument of mksquashfs)
    -m/--move           move files into a subdirectory of the squashfs
    -p/--no-chmod       do not set file permissions before squashing (to use if file permissions are already correct)
    -c/--no-compress    do not compress data, inode table or extended attributes (use options '$COMPRESS_OPTIONS' in mksquashfs call)
    -d/--dry-run        print commands but do not execute them
    -h/--help           print this message and exit

Example calls:
    $EXAMPLE_CALL
    sbatch --account <ACCOUNT> $EXAMPLE_CALL
HELPTEXT

# ========== FUNCTIONS ==========
function print_usage_and_exit() {
    EXIT_CODE="$1"
    if [ -z "$EXIT_CODE" ]
    then
        EXIT_CODE=0
    fi
    echo "$USAGE_STR"
    exit "$EXIT_CODE"
}

function print() {
    PREFIX="$1"
    MESSAGE="$2"
    if [[ -z "$MESSAGE" || -z "$PREFIX" ]]
    then
        echo "[ERROR] print() called with empty prefix or message"
        exit 3
    fi
    echo "[$PREFIX] $MESSAGE"
}

function info() {
    print "INFO" "$@"
}

function error() {
    print "ERROR" "$@"
    exit 1
}

function run() {
    COMMAND="$@"
    print "RUN" "$COMMAND"
    if [ -z "$DRY_RUN" ]
    then
        eval "$COMMAND"
        if [[ $? -ne 0 ]]
        then
            error "Command failed (return code $?): $COMMAND"
            exit 2
        fi
    fi
}

# ========== PARSE ARGS ==========
FPATH_OUTPUT=""
PATHS_TO_SQUASH=""
while [[ $# -gt 0 ]]
do
    case $1 in
        -h|--help)
            print_usage_and_exit
            ;;
        -d|--dry-run)
            DRY_RUN=1
            shift
            ;;
        -m|--move)
            DPATH_IN_SQUASH="$2"
            shift 2
            ;;
        -e|--exclude)
            FPATH_EXCLUDE="$2"
            shift 2
            ;;
        -c|--no-compress)
            NO_COMPRESS=1
            shift
            ;;
        -p|--no-chmod)
            NO_CHMOD=1
            shift
            ;;
        *)
            if [ -z "$FPATH_OUTPUT" ]
            then
                    FPATH_OUTPUT="$1"
            elif [ -z "$PATHS_TO_SQUASH" ]
            then
                PATHS_TO_SQUASH="$1"
            else
                PATHS_TO_SQUASH="$PATHS_TO_SQUASH $1"
            fi
            shift
            ;;
    esac
done

if [[ -z "$FPATH_OUTPUT" || -z "$PATHS_TO_SQUASH" ]]
then
    print_usage_and_exit 1
fi

# ========== CHECK ARGS ==========
if [ -f "$FPATH_OUTPUT" ]
then
    error "Output file already exists: $FPATH_OUTPUT"
elif [[ ! -z "$FPATH_EXCLUDE" && ! -f "$FPATH_EXCLUDE" ]]
then
    error "Exclude file does not exist: $FPATH_EXCLUDE"
elif [[ ! -z "${DPATH_IN_SQUASH:0:1}" && ! "${DPATH_IN_SQUASH:0:1}" == "/" ]]
then
    error "Path inside squashfs must be absolute, got $DPATH_IN_SQUASH"
else
    for PATH_TO_SQUASH in $PATHS_TO_SQUASH
    do
        if [[ ! -f "$PATH_TO_SQUASH" && ! -d "$PATH_TO_SQUASH" ]]
        then
            error "Path does not exist: $PATH_TO_SQUASH"
        fi
    done
fi

# ========== MAIN ==========
info "Start time: $(date)"
if [ ! -z "$SLURM_JOB_ID" ]
then
    TIMELIMIT="$(squeue -j ${SLURM_JOB_ID} -h --Format TimeLimit | xargs)"
    info "SLURM_JOB_ID:        $SLURM_JOB_ID"
    info "SLURM_MEM_PER_NODE:  $SLURM_MEM_PER_NODE"
    info "TIMELIMIT:           $TIMELIMIT"
fi
info "Output file: $FPATH_OUTPUT"
info "Squashing:   $PATHS_TO_SQUASH"
if [ ! -z "$FPATH_EXCLUDE" ]
then
    info "Excluding:   $FPATH_EXCLUDE"
    SQUASHFS_OPTIONS="$SQUASHFS_OPTIONS -ef $FPATH_EXCLUDE"
fi

if [ ! -z "$NO_COMPRESS" ]
then
    info "Not doing compression"
    SQUASHFS_OPTIONS="$SQUASHFS_OPTIONS $COMPRESS_OPTIONS"
fi

if [ ! -z "$NO_CHMOD" ]
then
    info "Keeping same file permissions"
fi

if [ ! -z "$DRY_RUN" ]
then
    info "Doing a dry run"
fi

# chmod
if [ -z "$NO_CHMOD" ]
then
    for PATH_TO_SQUASH in $PATHS_TO_SQUASH
    do
        run "chmod -R u+rwX,go+rX,go-w $PATH_TO_SQUASH"
    done
fi

run "mksquashfs $PATHS_TO_SQUASH $FPATH_OUTPUT $SQUASHFS_OPTIONS"

if [ ! -z "$DPATH_IN_SQUASH" ]
then
    info "Moving files into $DPATH_IN_SQUASH"

    # create a (hidden) empty file to add to the existing squashfs
    # then use -root-becomes to move previously squashed files to the correct location
    TMP_FILE="$TMPDIR/.mksquashfs-empty"
    touch $TMP_FILE
    trap 'rm -f "$TMP_FILE"' EXIT

    # move to $DATA_PATH
    while [ ! "$DPATH_IN_SQUASH" == "/" ]
    do
        DEST="$(basename $DPATH_IN_SQUASH)"
        DPATH_IN_SQUASH="$(dirname $DPATH_IN_SQUASH)"
        run "mksquashfs $TMP_FILE $FPATH_OUTPUT -root-becomes $DEST $SQUASHFS_OPTIONS >/dev/null"
    done
fi

info "End time: $(date)"
