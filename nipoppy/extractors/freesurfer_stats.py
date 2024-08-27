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
DEFAULT_MODE = MODE_SINGLE

DEFAULT_SUB_COLNAME = "participant_id"
DEFAULT_SES_COLNAME = "session_id"
DEFAULT_SUB_PREFIX = "sub-"
DEFAULT_SES_PREFIX = "ses-"


def _load_fs_tsv(
    tsv_path: Union[str, os.PathLike],
    sub_colname: str = DEFAULT_SUB_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
) -> pd.DataFrame:
    """Load a FreeSurfer stats TSV file and set the index to the subject ID.

    Parameters
    ----------
    tsv_path : Union[str, os.PathLike]
        Path to the TSV file.
    sub_colname : str, optional
        Column name to use for the subject ID in the final output file.
    sub_prefix : str, optional
        Prefix to strip from the subject IDs in the final output file.
        Set as empty string to keep the original values.

    Returns
    -------
    pd.DataFrame
        The TSV file as a DataFrame with a subject index.
    """
    df = pd.read_csv(tsv_path, sep="\t", index_col=0)
    df.index = df.index.str.removeprefix(sub_prefix)
    df.index.name = sub_colname
    return df


def _run_fs_command(
    fs_command: str,
    fs_subjects_dir: Union[str, os.PathLike],
    subjects_list: list[str],
    tsv_path: Union[str, os.PathLike],
    container_command_and_args: Optional[list[str]] = None,
    fs_args: Optional[list[str]] = None,
    sub_colname: str = DEFAULT_SUB_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
) -> pd.DataFrame:
    """Run a FreeSurfer {aparc,aseg}stats2table command and load the resulting TSV file.

    Parameters
    ----------
    fs_command : str
        FreeSurfer command to run.
    fs_subjects_dir : Union[str, os.PathLike]
        Path to the FreeSurfer subjects directory.
    subjects_list : list[str]
        List of subjects to process (i.e. subdirectories in fs_subjects_dir).
    tsv_path : Union[str, os.PathLike]
        Path to the output TSV file for this command.
    container_command_and_args : Optional[list[str]], optional
        Container command and arguments to prepend to actual FreeSurfer command.
    fs_args : Optional[list[str]], optional
        Other arguments for to FreeSurfer command.
    sub_colname : str, optional
        Passed to _load_fs_tsv.
    sub_prefix : str, optional
        Passed to _load_fs_tsv.

    Returns
    -------
    pd.DataFrame
        The output TSV file as a DataFrame.
    """
    # set defaults
    container_command_and_args = container_command_and_args or []
    fs_args = fs_args or []

    # process args for subprocess
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

    # run command with some feedback
    print(f"\nRunning {fs_command}")
    process = subprocess.run(args, env=env)
    if process.returncode != 0:
        sys.exit(
            f"\nError running command: {shlex.join(args)} "
            f"with environment variables: {env_vars}."
        )

    # return the output as a DataFrame
    return _load_fs_tsv(tsv_path, sub_colname=sub_colname, sub_prefix=sub_prefix)


def _run_asegstats2table(
    fs_subjects_dir: Union[str, os.PathLike],
    subjects_list: list[str],
    tsv_path: Union[str, os.PathLike],
    container_command_and_args: Optional[list[str]] = None,
    optional_args: Optional[list[str]] = None,
    sub_colname: str = DEFAULT_SUB_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
) -> pd.DataFrame:
    """Wrap _run_fs_command to run asegstats2table."""
    return _run_fs_command(
        container_command_and_args=container_command_and_args,
        fs_command="asegstats2table",
        fs_subjects_dir=fs_subjects_dir,
        subjects_list=subjects_list,
        tsv_path=tsv_path,
        fs_args=optional_args,
        sub_colname=sub_colname,
        sub_prefix=sub_prefix,
    )


def _run_aparcstats2table(
    fs_subjects_dir: Union[str, os.PathLike],
    subjects_list: list[str],
    tsv_path: Union[str, os.PathLike],
    hemi: str,
    container_command_and_args: Optional[list[str]] = None,
    optional_args: Optional[list[str]] = None,
    sub_colname: str = DEFAULT_SUB_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
) -> pd.DataFrame:
    """Wrap _run_fs_command to run aparcstats2table."""
    return _run_fs_command(
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
    """Extract FreeSurfer aseg and aparc statistics for a single subjects directory.

    This function calls _run_asegstats2table and _run_aparcstats2table (twice,
    once for each hemisphere) and concatenates the results into a single DataFrame.

    Parameters
    ----------
    subjects_dir_path : Union[str, os.PathLike]
        Path to the FreeSurfer subjects directory.
    container_command_and_args : Optional[list[str]], optional
        Passed to _run_asegstats2table and _run_aparcstats2table.
    aseg_optional_args : Optional[list[str]], optional
        Passed to _run_asegstats2table.
    aparc_optional_args : Optional[list[str]], optional
        Passed to _run_aparcstats2table.
    sub_colname : str, optional
        Passed to run_asegstats2table and _run_aparcstats2table.
    sub_prefix : str, optional
        Passed to run_asegstats2table and _run_aparcstats2table.

    Returns
    -------
    pd.DataFrame
        DataFrame with subject index and FreeSurfer stats columns.
    """
    # get all subjects except fsaverage
    subjects = [
        dpath.name
        for dpath in Path(subjects_dir_path).iterdir()
        if dpath.name != "fsaverage" and dpath.is_dir()
    ]

    # create a temporary directory to store the stats files (will be deleted)
    # we do not need the individuals files after they are combined
    with tempfile.TemporaryDirectory(dir=subjects_dir_path) as tmpdir:
        tmpdir = Path(tmpdir)
        df_aseg = _run_asegstats2table(
            fs_subjects_dir=subjects_dir_path,
            subjects_list=subjects,
            tsv_path=tmpdir / "aseg_stats.tsv",
            container_command_and_args=container_command_and_args,
            optional_args=aseg_optional_args,
            sub_colname=sub_colname,
            sub_prefix=sub_prefix,
        )

        df_aparc_lh = _run_aparcstats2table(
            fs_subjects_dir=subjects_dir_path,
            subjects_list=subjects,
            tsv_path=tmpdir / "aparc_stats_lh.tsv",
            hemi="lh",
            container_command_and_args=container_command_and_args,
            optional_args=aparc_optional_args,
            sub_colname=sub_colname,
            sub_prefix=sub_prefix,
        )

        df_aparc_rh = _run_aparcstats2table(
            fs_subjects_dir=subjects_dir_path,
            subjects_list=subjects,
            tsv_path=tmpdir / "aparc_stats_rh.tsv",
            hemi="rh",
            container_command_and_args=container_command_and_args,
            optional_args=aparc_optional_args,
            sub_colname=sub_colname,
            sub_prefix=sub_prefix,
        )

    # combine the stats files and make sure there are no duplicate column names
    df_stats = pd.concat([df_aseg, df_aparc_lh, df_aparc_rh], axis="columns")
    if len(set(df_stats.columns)) != len(df_stats.columns):
        sys.exit("Duplicate column names in the stats files.")
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
    """Extract FreeSurfer aseg and aparc statistics for multiple sessions.

    This function calls run_single for each session and concatenates the results
    with a session level in the index.

    Parameters
    ----------
    sessions_dir_path : Union[str, os.PathLike]
        Path containing multiple FreeSurfer subjects directories, one for each session.
    container_command_and_args : Optional[list[str]], optional
        Passed to run_single.
    aparc_optional_args : Optional[list[str]], optional
        Passed to run_single.
    aseg_optional_args : Optional[list[str]], optional
        Passed to run_single.
    sub_colname : str, optional
        Passed to run_single.
    ses_colname : str, optional
        Passed to run_single.
    sub_prefix : str, optional
        Prefix to strip from the subject IDs in the final output file.
        Set as empty string to keep the original values.
    ses_prefix : str, optional
        Prefix to strip from the session IDs in the final output file.
        Set as empty string to keep the original values.

    Returns
    -------
    pd.DataFrame
        DataFrame with multi-level index (subject, session)and FreeSurfer stats
        columns.
    """
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

    # combine the dataframes and update the index
    df_stats = pd.concat(session_df_map, names=[ses_colname])
    df_stats.index = df_stats.index.reorder_levels([sub_colname, ses_colname])
    df_stats = df_stats.sort_index()
    return df_stats


def run(
    input_dir_path: Union[str, os.PathLike],
    output_file_path: Union[str, os.PathLike],
    mode: str = DEFAULT_MODE,
    container_command_and_args: Optional[list[str]] = None,
    aparc_optional_args: Optional[list[str]] = None,
    aseg_optional_args: Optional[list[str]] = None,
    sub_colname: str = DEFAULT_SUB_COLNAME,
    ses_colname: str = DEFAULT_SES_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
    ses_prefix: str = DEFAULT_SES_PREFIX,
):
    """Extract FreeSurfer aseg and aparc statistics into a single file.

    This extractor uses FreeSurfer's asegstats2table and aparcstats2table, and so
    requires FreeSurfer installation or a container with FreeSurfer available.

    Parameters
    ----------
    input_dir_path : Union[str, os.PathLike]
        Path to input directory, which should be a FreeSurfer subjects directory if
        mode is "single" or a directory containing multiple FreeSurfer subjects
        directories if mode is "multi".
    output_file_path : Union[str, os.PathLike]
        Path to the output TSV file. The parent directory of this path must exist.
    mode : str
        See input_dir_path.
    container_command_and_args : Optional[list[str]], optional
        Container command and arguments (including image file), by default None.
        This needs to contain everything needed to be able to run the
        FreeSurfer commands, for example ["apptainer", "exec", "--bind",
        "<INPUT_DIR_PATH>", "<IMAGE_FILE_PATH>"]. Does not need to be specified
        if running on a system with FreeSurfer installed. IMPORTANT: only the
        Singularity/Apptainer container engine is explicitly supported because it
        allows for forwarding environment variables; this function might work with
        Docker containers but likely only with --mode "single".
    aparc_optional_args : Optional[list[str]], optional
        Optional arguments to pass to aparcstats2table, by default None
    aseg_optional_args : Optional[list[str]], optional
        Optional arguments to pass to asegstats2table, by default None
    sub_colname : str, optional
        Column name to use for the subject ID in the final output file.
    ses_colname : str, optional
        Column name to use for the session ID in the final output file.
    sub_prefix : str, optional
        Prefix to strip from the subject IDs in the final output file.
        Set as empty string to keep the original values.
    ses_prefix : str, optional
        Prefix to strip from the session IDs in the final output file.
        Set as empty string to keep the original values.
    """
    # single subjects directory (no sessions)
    if mode == MODE_SINGLE:
        df_stats = run_single(
            subjects_dir_path=input_dir_path,
            aseg_optional_args=aseg_optional_args,
            aparc_optional_args=aparc_optional_args,
            container_command_and_args=container_command_and_args,
            sub_colname=sub_colname,
            sub_prefix=sub_prefix,
        )

    # multiple subjects directories (assumed to be sessions)
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

    # save final file
    df_stats.to_csv(output_file_path, sep="\t")
    print(
        "\nSaved aggregated stats file with shape "
        f"{df_stats.shape} to {output_file_path}."
    )


def build_parser() -> argparse.ArgumentParser:
    """Create the parser for the CLI."""
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
        default=DEFAULT_MODE,
        help=(
            "Whether to process a single FreeSurfer subjects directory or multiple "
            f"directories (default: {DEFAULT_MODE})."
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
    return parser


if __name__ == "__main__":

    parser = build_parser()
    args = parser.parse_args()
    run(
        input_dir_path=args.input_dir_path,
        output_file_path=args.output_file_path,
        mode=args.mode,
        container_command_and_args=shlex.split(args.container),
        aseg_optional_args=shlex.split(args.aseg_args),
        aparc_optional_args=shlex.split(args.aparc_args),
        sub_colname=args.sub_colname,
        ses_colname=args.ses_colname,
        sub_prefix=args.sub_prefix,
        ses_prefix=args.ses_prefix,
    )
