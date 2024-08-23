#!/usr/bin/env python
"""Extractor for FreeSurfer aseg and aparc stats."""

import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Union

import pandas as pd

MODE_SINGLE = "single"
MODE_MULTI = "multi"

DEFAULT_SUB_COLNAME = "participant_id"
DEFAULT_SES_COLNAME = "session_id"
DEFAULT_SUB_PREFIX = "sub-"
DEFAULT_SES_PREFIX = "ses-"


def load_fs_tsv(
    tsv_path: Union[str, os.PathLike],
    sub_colname: str = DEFAULT_SUB_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
) -> pd.DataFrame:
    df = pd.read_csv(tsv_path, sep="\t", index_col=0)
    df.index = df.index.str.removeprefix(sub_prefix)
    df.index.name = sub_colname
    return df


def run_fs_command(
    fs_command: str,
    fs_subjects_dir: Union[str, os.PathLike],
    subjects_list: list[str],
    tsv_path: Union[str, os.PathLike],
    container_command_and_args: Optional[list[str]] = None,
    fs_args: Optional[list[str]] = None,
    sub_colname: str = DEFAULT_SUB_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
) -> pd.DataFrame:
    container_command_and_args = container_command_and_args or []
    fs_args = fs_args or []

    # process args
    args = (
        container_command_and_args
        + [fs_command, "--subjects"]
        + subjects_list
        + [f"--tablefile={tsv_path}"]
        + fs_args
    )
    args = [str(arg) for arg in args]

    # set environment variables
    env_vars = {
        "SUBJECTS_DIR": fs_subjects_dir,
        "APPTAINERENV_SUBJECTS_DIR": fs_subjects_dir,
        "SINGULARITYENV_SUBJECTS_DIR": fs_subjects_dir,
    }
    env = os.environ.copy()
    env.update(env_vars)

    print(f"\nRunning {fs_command}")
    process = subprocess.run(args, env=env)
    if process.returncode != 0:
        sys.exit(
            f"\nError running command: {shlex.join(args)} "
            f"with environment variables: {env_vars}."
        )
    return load_fs_tsv(tsv_path, sub_colname=sub_colname, sub_prefix=sub_prefix)


def run_asegstats2table(
    fs_subjects_dir: Union[str, os.PathLike],
    subjects_list: list[str],
    tsv_path: Union[str, os.PathLike],
    container_command_and_args: Optional[list[str]] = None,
    optional_args: Optional[list[str]] = None,
    sub_colname: str = DEFAULT_SUB_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
) -> pd.DataFrame:
    return run_fs_command(
        container_command_and_args=container_command_and_args,
        fs_command="asegstats2table",
        fs_subjects_dir=fs_subjects_dir,
        subjects_list=subjects_list,
        tsv_path=tsv_path,
        fs_args=optional_args,
        sub_colname=sub_colname,
        sub_prefix=sub_prefix,
    )


def run_aparcstats2table(
    fs_subjects_dir: Union[str, os.PathLike],
    subjects_list: list[str],
    tsv_path: Union[str, os.PathLike],
    hemi: str,
    container_command_and_args: Optional[list[str]] = None,
    optional_args: Optional[list[str]] = None,
    sub_colname: str = DEFAULT_SUB_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
) -> pd.DataFrame:
    return run_fs_command(
        container_command_and_args=container_command_and_args,
        fs_command="aparcstats2table",
        fs_subjects_dir=fs_subjects_dir,
        subjects_list=subjects_list,
        tsv_path=tsv_path,
        fs_args=[f"--hemi={hemi}"] + optional_args,
        sub_colname=sub_colname,
        sub_prefix=sub_prefix,
    )


def run_single(
    subjects_dir_path: Union[str, os.PathLike],
    container_command_and_args: Optional[list[str]] = None,
    aseg_optional_args: Optional[list[str]] = None,
    aparc_optional_args: Optional[list[str]] = None,
    sub_colname: str = DEFAULT_SUB_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
) -> pd.DataFrame:

    # get all subjects except fsaverage
    subjects = [
        dpath.name
        for dpath in Path(subjects_dir_path).iterdir()
        if dpath.name != "fsaverage" and dpath.is_dir()
    ]

    with tempfile.TemporaryDirectory(dir=subjects_dir_path) as tmpdir:
        tmpdir = Path(tmpdir)
        df_aseg = run_asegstats2table(
            fs_subjects_dir=subjects_dir_path,
            subjects_list=subjects,
            tsv_path=tmpdir / "aseg_stats.tsv",
            container_command_and_args=container_command_and_args,
            optional_args=aseg_optional_args,
            sub_colname=sub_colname,
            sub_prefix=sub_prefix,
        )

        df_aparc_lh = run_aparcstats2table(
            fs_subjects_dir=subjects_dir_path,
            subjects_list=subjects,
            tsv_path=tmpdir / "aparc_stats_lh.tsv",
            hemi="lh",
            container_command_and_args=container_command_and_args,
            optional_args=aparc_optional_args,
            sub_colname=sub_colname,
            sub_prefix=sub_prefix,
        )

        df_aparc_rh = run_aparcstats2table(
            fs_subjects_dir=subjects_dir_path,
            subjects_list=subjects,
            tsv_path=tmpdir / "aparc_stats_rh.tsv",
            hemi="rh",
            container_command_and_args=container_command_and_args,
            optional_args=aparc_optional_args,
            sub_colname=sub_colname,
            sub_prefix=sub_prefix,
        )

    df_stats = pd.concat([df_aseg, df_aparc_lh, df_aparc_rh], axis="columns")
    if len(set(df_stats.columns)) != len(df_stats.columns):
        sys.exit("Overlapping column names in the stats files. Cannot merge.")
    df_stats = df_stats.sort_index()

    return df_stats


def run_multi(
    sessions_dir_path: Union[str, os.PathLike],
    container_command_and_args: Optional[list[str]] = None,
    aparc_optional_args: Optional[list[str]] = None,
    aseg_optional_args: Optional[list[str]] = None,
    sub_colname: str = DEFAULT_SUB_COLNAME,
    ses_colname: str = DEFAULT_SES_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
    ses_prefix: str = DEFAULT_SES_PREFIX,
) -> pd.DataFrame:
    sessions_dir_path = Path(sessions_dir_path)

    # get a dataframe for each session
    session_df_map = {}
    for dpath_session in sessions_dir_path.iterdir():
        if not dpath_session.is_dir():
            continue
        session_df_map[dpath_session.name.removeprefix(ses_prefix)] = run_single(
            subjects_dir_path=dpath_session,
            container_command_and_args=container_command_and_args,
            aseg_optional_args=aseg_optional_args,
            aparc_optional_args=aparc_optional_args,
            sub_colname=sub_colname,
            sub_prefix=sub_prefix,
        )

    df_stats = pd.concat(session_df_map, names=[ses_colname])
    df_stats.index = df_stats.index.reorder_levels([sub_colname, ses_colname])
    df_stats = df_stats.sort_index()
    return df_stats


def run(
    input_dir_path: Union[str, os.PathLike],
    output_file_path: Union[str, os.PathLike],
    mode: str,
    container_command_and_args: Optional[list[str]] = None,
    aparc_optional_args: Optional[list[str]] = None,
    aseg_optional_args: Optional[list[str]] = None,
    sub_colname: str = DEFAULT_SUB_COLNAME,
    ses_colname: str = DEFAULT_SES_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
    ses_prefix: str = DEFAULT_SES_PREFIX,
):
    container_command_and_args = container_command_and_args or []
    aparc_optional_args = aparc_optional_args or []
    aseg_optional_args = aseg_optional_args or []
    if mode == MODE_SINGLE:
        df_stats = run_single(
            subjects_dir_path=input_dir_path,
            aseg_optional_args=aseg_optional_args,
            aparc_optional_args=aparc_optional_args,
            container_command_and_args=container_command_and_args,
            sub_colname=sub_colname,
            sub_prefix=sub_prefix,
        )
    elif mode == MODE_MULTI:
        df_stats = run_multi(
            sessions_dir_path=input_dir_path,
            aseg_optional_args=aseg_optional_args,
            aparc_optional_args=aparc_optional_args,
            container_command_and_args=container_command_and_args,
            sub_colname=sub_colname,
            sub_prefix=sub_prefix,
            ses_colname=ses_colname,
            ses_prefix=ses_prefix,
        )
    else:
        sys.exit(f"\nInvalid mode: {mode}. Must be one of: {MODE_SINGLE}, {MODE_MULTI}")

    df_stats.to_csv(output_file_path, sep="\t")
    print(
        f"\nSaved aggregated stats file with shape {df_stats.shape} to {output_file_path}."
    )


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Get combined FreeSurfer stats using asegstats2table and aparcstats2table. "
            "Returns a single TSV file with all the stats. "
            "Optionally handle multiple sessions (i.e. when the input directory "
            "contains multiple FreeSurfer subjects directories, one for each session)."
        )
    )

    # CLI inputs
    parser.add_argument(
        "input_dir_path",
        type=Path,
        help=(
            "Path to the input directory. Can be either a single FreeSurfer subjects "
            f'directories (if "--mode {MODE_SINGLE}" is used) or a directory '
            f'containing multiple FreeSurfer directories (if "--mode {MODE_MULTI}" '
            "is used)."
        ),
    )
    parser.add_argument(
        "output_file_path",
        type=Path,
        help="Path to the output TSV file.",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=[MODE_SINGLE, MODE_MULTI],
        default=MODE_SINGLE,
        help=(
            "Whether to process a single FreeSurfer subjects directory or multiple "
            f"directories (default: {MODE_SINGLE})."
        ),
    )
    parser.add_argument(
        "--container",
        type=str,
        default="",
        help=(
            "Container command and arguments (including image file), as a single "
            "string. This needs to contain everything needed to be able to run the "
            'FreeSurfer commands, for example "apptainer exec --bind <INPUT_DIR_PATH> '
            '<IMAGE_FILE_PATH>". Does not need to be specified if running on a system '
            "with FreeSurfer installed. IMPORTANT: only the Singularity/Apptainer "
            "container engine is explicitly supported because it allows for "
            "forwarding environment variables; this script might work with Docker "
            f"containers but likely only with --mode {MODE_SINGLE}."
        ),
    )
    parser.add_argument(
        "--aseg-args",
        type=str,
        default="",
        help="Optional arguments to pass to asegstats2table, as a single string.",
    )
    parser.add_argument(
        "--aparc-args",
        type=str,
        default="",
        help="Optional arguments to pass to aparcstats2table, as a single string.",
    )
    parser.add_argument(
        "--sub-colname",
        type=str,
        default=DEFAULT_SUB_COLNAME,
        help=(
            "Column name to use for the subject ID in the final output file "
            f'(default: "{DEFAULT_SUB_COLNAME}").'
        ),
    )
    parser.add_argument(
        "--ses-colname",
        type=str,
        default=DEFAULT_SES_COLNAME,
        help=(
            "Column name to use for the session ID in the final output file "
            f'(default: "{DEFAULT_SES_COLNAME}").'
        ),
    )
    parser.add_argument(
        "--sub-prefix",
        type=str,
        default=DEFAULT_SUB_PREFIX,
        help=(
            "Prefix to strip from the subject IDs in the final output file "
            f'(default: "{DEFAULT_SUB_PREFIX}"). Set as empty string to keep the '
            "original values."
        ),
    )
    parser.add_argument(
        "--ses-prefix",
        type=str,
        default=DEFAULT_SES_PREFIX,
        help=(
            "Prefix to strip from the session IDs in the final output file "
            f'(default: "{DEFAULT_SES_PREFIX}"). Set as empty string to keep the '
            "original values."
        ),
    )

    args = parser.parse_args()
    run(
        input_dir_path=args.input_dir_path,
        output_file_path=args.output_file_path,
        mode=args.mode,
        container_command_and_args=shlex.split(args.container),
        aseg_optional_args=shlex.split(args.aseg_optional_args),
        aparc_optional_args=shlex.split(args.aparc_optional_args),
        sub_colname=args.sub_colname,
        ses_colname=args.ses_colname,
        sub_prefix=args.sub_prefix,
        ses_prefix=args.ses_prefix,
    )
