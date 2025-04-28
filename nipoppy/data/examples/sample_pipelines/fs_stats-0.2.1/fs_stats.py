#!/usr/bin/env python
"""Extractor for FreeSurfer aseg/aparc stats and quality control metrics."""

import argparse
import os
import re
import shlex
import subprocess
import sys
import tempfile
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Optional, Tuple, Union

import pandas as pd

MODE_SINGLE = "single"
MODE_MULTI = "multi"
DEFAULT_MODE = MODE_SINGLE

DEFAULT_ASEG_MEASURES = ["volume"]
DEFAULT_APARC_PARCELLATIONS = ["aparc", "aparc.a2009s", "aparc.DKTatlas"]
DEFAULT_APARC_MEASURES = ["thickness", "area", "meancurv"]

DEFAULT_EULER_SURF_PATHS = [
    "surf/lh.white",
    "surf/rh.white",
    "surf/lh.pial",
    "surf/rh.pial",
]
DEFAULT_CNR_VOL_PATHS = ["mri/norm.mgz"]
DEFAULT_CNR_COLS = ["gray_white_cnr", "gray_csf_cnr"]
ALL_CNR_COLS = [
    "gray_white_cnr",
    "gray_csf_cnr",
    "white_mean",
    "gray_mean",
    "csf_mean",
    "sqrt_white_var",
    "sqrt_gray_var",
    "sqrt_csf_var",
]

DEFAULT_SUB_COLNAME = "participant_id"
DEFAULT_SES_COLNAME = "session_id"
DEFAULT_SUB_PREFIX = "sub-"
DEFAULT_SES_PREFIX = "ses-"

RE_FS_VERSION = re.compile(r"[\d]\.[\d]\.[\d]")
FNAME_FS_VERSION = "build-stamp.txt"


def _print_error_and_exit(message: str):
    sys.exit(f"\nERROR: {message}\nStopping fs_stats\n")


def _get_fs_version(dpath, fname_version=FNAME_FS_VERSION, re_version=RE_FS_VERSION):
    """
    Search for a version file and extract FreeSurfer version from it.

    This assumes dpath only contains results from a single FreeSurfer version.
    Returns None if no version file file is found or if the version could not be
    extracted.
    """
    fs_version = None
    for fpath in Path(dpath).rglob(fname_version):
        if fpath.is_file():
            if match := re_version.search(fpath.read_text()):
                fs_version = match.group()
                break
    return fs_version


def _load_fs_stats_table(
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


def _run_subprocess(args, verbose=False, **kwargs) -> subprocess.CompletedProcess:
    """Run a subprocess with optional verbosity."""
    if verbose:
        print(f"\nRunning command: {shlex.join(args)}\n")
    else:
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
    return subprocess.run(args, **kwargs)


def _run_fs_stats2table_command(
    fs_command: str,
    fs_subjects_dir: Union[str, os.PathLike],
    subjects_list: list[str],
    tsv_path: Union[str, os.PathLike],
    container_command_and_args: Optional[list[str]] = None,
    fs_args: Optional[list[str]] = None,
    sub_colname: str = DEFAULT_SUB_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
    verbose: bool = False,
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
    verbose : bool, optional
        Passed to _run_subprocess.

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
    process = _run_subprocess(args, env=env, verbose=verbose)
    if process.returncode != 0:
        error_message = (
            f"Error running command: {shlex.join(args)} "
            f"with environment variables: {env_vars}."
        )
        if not verbose:
            error_message += (
                " Tip: rerun the same command with the --verbose flag "
                "to see the output of the FreeSurfer command."
            )
        _print_error_and_exit(error_message)

    # return the output as a DataFrame
    return _load_fs_stats_table(
        tsv_path, sub_colname=sub_colname, sub_prefix=sub_prefix
    )


def _run_asegstats2table(
    fs_subjects_dir: Union[str, os.PathLike],
    subjects_list: list[str],
    tsv_path: Union[str, os.PathLike],
    container_command_and_args: Optional[list[str]] = None,
    optional_args: Optional[list[str]] = None,
    sub_colname: str = DEFAULT_SUB_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
    verbose: bool = False,
) -> pd.DataFrame:
    """Wrap _run_fs_command to run asegstats2table."""
    return _run_fs_stats2table_command(
        container_command_and_args=container_command_and_args,
        fs_command="asegstats2table",
        fs_subjects_dir=fs_subjects_dir,
        subjects_list=subjects_list,
        tsv_path=tsv_path,
        fs_args=optional_args,
        sub_colname=sub_colname,
        sub_prefix=sub_prefix,
        verbose=verbose,
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
    verbose: bool = False,
) -> pd.DataFrame:
    """Wrap _run_fs_command to run aparcstats2table."""
    return _run_fs_stats2table_command(
        container_command_and_args=container_command_and_args,
        fs_command="aparcstats2table",
        fs_subjects_dir=fs_subjects_dir,
        subjects_list=subjects_list,
        tsv_path=tsv_path,
        fs_args=[f"--hemi={hemi}"] + optional_args,
        sub_colname=sub_colname,
        sub_prefix=sub_prefix,
        verbose=verbose,
    )


def _run_mris_euler_number(
    surf_path: Union[str, os.PathLike],
    out_path: Union[str, os.PathLike],
    container_command_and_args: Optional[list[str]] = None,
    verbose: bool = False,
) -> int:
    """Return the number of holes computed by FreeSurfer's mris_euler_number.

    Parameters
    ----------
    surf_path : Union[str, os.PathLike]
        Input surface file.
    out_path : Union[str, os.PathLike]
        File to write the number of holes to.
    container_command_and_args : Optional[list[str]], optional
        Container command and arguments to prepend to actual FreeSurfer command.
    verbose : bool, optional
        Passed to _run_subprocess.

    Returns
    -------
    int
    """
    container_command_and_args = container_command_and_args or []

    # process args for subprocess
    args = container_command_and_args + ["mris_euler_number", "-o", out_path, surf_path]
    args = [str(arg) for arg in args]

    # run command with some feedback
    process = _run_subprocess(args, verbose=verbose, check=True)
    if process.returncode != 0:
        _print_error_and_exit(f"Error running command: {shlex.join(args)}")

    # return the number of holes
    return int(Path(out_path).read_text().strip())


def _run_mri_cnr(
    surf_dir: Union[str, os.PathLike],
    vol_paths: list[Union[str, os.PathLike]],
    out_path: Union[str, os.PathLike],
    container_command_and_args: Optional[list[str]] = None,
    verbose: bool = False,
) -> pd.DataFrame:
    """Return the (2*len(vol_paths), 8) CNR values from FreeSurfer's mri_cnr.

    Parameters
    ----------
    surf_dir : Union[str, os.PathLike]
        _description_
    vol_paths : list[Union[str, os.PathLike]]
        _description_
    out_path : Union[str, os.PathLike]
        _description_
    container_command_and_args : Optional[list[str]], optional
        Container command and arguments to prepend to actual FreeSurfer command.
    verbose : bool, optional
        Passed to _run_subprocess.

    Returns
    -------
    pd.DataFrame
    """
    container_command_and_args = container_command_and_args or []

    # process args for subprocess
    args = (
        container_command_and_args + ["mri_cnr", "-l", out_path, surf_dir] + vol_paths
    )
    args = [str(arg) for arg in args]

    # run command with some feedback
    process = _run_subprocess(args, verbose=verbose, check=True)
    if process.returncode != 0:
        _print_error_and_exit(f"Error running command: {shlex.join(args)}")

    # return the 8 CNR values
    index = []
    for vol_path in vol_paths:
        for hemi in ["lh", "rh"]:
            index.append((Path(vol_path).name, hemi))

    df = pd.read_csv(out_path, sep=r"\s+", header=None, names=ALL_CNR_COLS)
    df.index = index

    return df


def _get_subject_list(
    fs_subjects_dir: Union[str, os.PathLike], using_container=False
) -> list[str]:
    """Get a list of subjects in a FreeSurfer subjects directory."""
    subject_list = []
    for dpath in Path(fs_subjects_dir).iterdir():
        if dpath.name == "fsaverage":
            continue

        if dpath.is_symlink():
            if not dpath.resolve().exists():
                _print_error_and_exit(f"Found broken symlink: {dpath}")

            # potential source of error that leads to unclear FreeSurfer error message
            if using_container:
                warnings.warn(
                    "Found symlink(s) in the subjects directory. Make sure the symlink "
                    "target path(s) are mounted correctly in the container."
                )

        subject_list.append(dpath.name)

    if not subject_list:
        _print_error_and_exit(f"No subjects found in {fs_subjects_dir}")
    return subject_list


def run_single_aseg(
    subjects_dir_path: Union[str, os.PathLike],
    container_command_and_args: Optional[list[str]] = None,
    measures: list[str] = DEFAULT_ASEG_MEASURES,
    optional_args: Optional[list[str]] = None,
    sub_colname: str = DEFAULT_SUB_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
    verbose: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Extract FreeSurfer aseg and aparc statistics for a single subjects directory.

    This function calls _run_asegstats2table and _run_aparcstats2table (twice,
    once for each hemisphere) and concatenates the results into a single DataFrame.

    Parameters
    ----------
    subjects_dir_path : Union[str, os.PathLike]
        Path to the FreeSurfer subjects directory.
    container_command_and_args : Optional[list[str]], optional
        Passed to _run_asegstats2table.
    measures: list[str], optional
        List of measures to use for asegstats2table.
    optional_args : Optional[list[str]], optional
        Passed to _run_asegstats2table.
    sub_colname : str, optional
        Passed to run_asegstats2table.
    sub_prefix : str, optional
        Passed to run_asegstats2table.
    verbose : bool, optional
        Passed to _run_subprocess.

    Returns
    -------
    dict[str, pd.DataFrame]
        Keys are measure names.
        Values are dataframes for aseg stats, with subject index.
    """
    subjects = _get_subject_list(
        subjects_dir_path, using_container=container_command_and_args
    )
    dfs_aseg = {}

    # create a temporary directory to store the stats files (will be deleted)
    # we do not need the individuals files after they are combined
    with tempfile.TemporaryDirectory(dir=subjects_dir_path) as tmpdir:
        tmpdir = Path(tmpdir)

        for measure in measures:

            print(f'Getting aseg stats for measure "{measure}"')

            optional_args_all = optional_args + ["--meas", measure]

            df_aseg = _run_asegstats2table(
                fs_subjects_dir=subjects_dir_path,
                subjects_list=subjects,
                tsv_path=tmpdir / f"aseg_stats-{measure}.tsv",
                container_command_and_args=container_command_and_args,
                optional_args=optional_args_all,
                sub_colname=sub_colname,
                sub_prefix=sub_prefix,
                verbose=verbose,
            )

            dfs_aseg[measure] = df_aseg.sort_index()

    return dfs_aseg


def run_single_aparc(
    subjects_dir_path: Union[str, os.PathLike],
    container_command_and_args: Optional[list[str]] = None,
    parcellations: list[str] = DEFAULT_APARC_PARCELLATIONS,
    measures: list[str] = DEFAULT_APARC_MEASURES,
    optional_args: Optional[list[str]] = None,
    sub_colname: str = DEFAULT_SUB_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
    verbose: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Extract FreeSurfer aseg and aparc statistics for a single subjects directory.

    This function calls _run_aparcstats2table (twice, once for each hemisphere) and
    concatenates the results into a single DataFrame.

    Parameters
    ----------
    subjects_dir_path : Union[str, os.PathLike]
        Path to the FreeSurfer subjects directory.
    container_command_and_args : Optional[list[str]], optional
        Passed _run_aparcstats2table.
    parcellations : list[str], optional
        List of parcellations to use for _run_aparcstats2table.
    measures: list[str], optional
        List of measures to use for _run_aparcstats2table.
    optional_args : Optional[list[str]], optional
        Passed to _run_aparcstats2table.
    sub_colname : str, optional
        Passed to _run_aparcstats2table.
    sub_prefix : str, optional
        Passed to _run_aparcstats2table.
    verbose : bool, optional
        Passed to _run_subprocess.

    Returns
    -------
    dict[Tuple[str, str], pd.DataFrame]
        Keys are tuples of parcellation and measure names.
        Values are dataframes for aparc stats, with subject index.
    """
    subjects = _get_subject_list(
        subjects_dir_path, using_container=container_command_and_args
    )
    dfs_aparc = {}

    # create a temporary directory to store the stats files (will be deleted)
    # we do not need the individuals files after they are combined
    with tempfile.TemporaryDirectory(dir=subjects_dir_path) as tmpdir:
        tmpdir = Path(tmpdir)

        # get one df per parcellation and measure combination
        for parcellation in parcellations:
            for measure in measures:

                print(
                    "Getting aparc stats for "
                    f'parcellation "{parcellation}" and measure "{measure}"'
                )

                optional_args_all = optional_args + [
                    f"--parc={parcellation}",
                    f"--measure={measure}",
                ]

                df_aparc_lh = _run_aparcstats2table(
                    fs_subjects_dir=subjects_dir_path,
                    subjects_list=subjects,
                    tsv_path=tmpdir / f"aparc_stats_lh-{parcellation}-{measure}.tsv",
                    hemi="lh",
                    container_command_and_args=container_command_and_args,
                    optional_args=optional_args_all,
                    sub_colname=sub_colname,
                    sub_prefix=sub_prefix,
                    verbose=verbose,
                )

                df_aparc_rh = _run_aparcstats2table(
                    fs_subjects_dir=subjects_dir_path,
                    subjects_list=subjects,
                    tsv_path=tmpdir / f"aparc_stats_rh-{parcellation}-{measure}.tsv",
                    hemi="rh",
                    container_command_and_args=container_command_and_args,
                    optional_args=optional_args_all,
                    sub_colname=sub_colname,
                    sub_prefix=sub_prefix,
                    verbose=verbose,
                )

                # FreeSurfer 6 has duplicate columns between files
                for col in ["BrainSegVolNotVent", "eTIV"]:
                    first = None
                    for df_to_concat in [df_aparc_lh, df_aparc_rh]:
                        if col in df_to_concat:
                            if first is None:
                                first = df_to_concat[col]
                            else:
                                common_participants = list(
                                    set(first.index).intersection(
                                        set(df_to_concat.index)
                                    )
                                )
                                if first.loc[common_participants].equals(
                                    df_to_concat.loc[common_participants, col]
                                ):
                                    df_to_concat.drop(col, axis="columns", inplace=True)
                                    print(
                                        f"\tDropped duplicate column {col}"
                                        " from aparc file."
                                    )

                # combine the aparc stats files
                # and make sure there are no duplicate column names
                df_aparc = pd.concat([df_aparc_lh, df_aparc_rh], axis="columns")
                if len(set(df_aparc.columns)) != len(df_aparc.columns):
                    _print_error_and_exit(
                        "Duplicate column names in the stats files: "
                        f"{df_aparc.columns[df_aparc.columns.duplicated()]}"
                    )

                # sort and return
                df_aparc = df_aparc.sort_index()
                dfs_aparc[(parcellation, measure)] = df_aparc

    return dfs_aparc


def run_single_qc(
    subjects_dir_path: Union[str, os.PathLike],
    euler_surf_paths: list[Union[str, os.PathLike]] = DEFAULT_EULER_SURF_PATHS,
    cnr_vol_paths: list[Union[str, os.PathLike]] = DEFAULT_CNR_VOL_PATHS,
    cnr_cols: list[str] = DEFAULT_CNR_COLS,
    container_command_and_args: Optional[list[str]] = None,
    sub_colname: str = DEFAULT_SUB_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
    verbose: bool = False,
) -> pd.DataFrame:
    """Extract FreeSurfer QC metrics for a single subjects directory.

    This function calls _run_mris_euler_number and _run_mri_cnr for each subject
    and concatenates the results into a single DataFrame.

    Parameters
    ----------
    subjects_dir_path : Union[str, os.PathLike]
        Path to the FreeSurfer subjects directory.
    euler_surf_paths : list[Union[str, os.PathLike]], optional
        Paths to the surface files to calculate the Euler number from, relative
        to subjects_dir_path.
    cnr_vol_paths : list[Union[str, os.PathLike]], optional
        Paths to the volume files to calculate the contrast-to-noise ratio from,
        relative to subjects_dir_path.
    cnr_cols : list[str], optional
        Names of the CNR measures to include in the QC metrics file for each volume.
    container_command_and_args : Optional[list[str]], optional
        Passed to _run_mris_euler_number and _run_mri_cnr.
    sub_colname : str, optional
        Column name to use for the subject ID in the final output file.
    sub_prefix : str, optional
        Prefix to strip from the subject IDs in the final output file.
        Set as empty string to keep the original values.
    verbose : bool, optional
        Passed to _run_subprocess.

    Returns
    -------
    pd.DataFrame
    """
    subjects_dir_path = Path(subjects_dir_path)
    euler_surf_paths: list[Path] = [Path(surf_path) for surf_path in euler_surf_paths]

    print("Getting QC metrics")

    data_for_df = []
    subjects = _get_subject_list(
        subjects_dir_path, using_container=container_command_and_args
    )
    with tempfile.TemporaryDirectory(dir=subjects_dir_path) as tmpdir:
        for subject in subjects:
            data_subject = {sub_colname: subject.removeprefix(sub_prefix)}

            # get number of holes in surface files based on Euler number
            for surf_path in euler_surf_paths:
                out_path = Path(tmpdir) / f"{subject}_euler_{surf_path.name}.txt"
                try:
                    data_subject[f"n_holes-{surf_path.name.replace('.', '_')}"] = (
                        _run_mris_euler_number(
                            surf_path=subjects_dir_path / subject / surf_path,
                            out_path=out_path,
                            container_command_and_args=container_command_and_args,
                            verbose=verbose,
                        )
                    )
                except subprocess.CalledProcessError:
                    print(f"\tError calculating Euler number for {surf_path.name}.")

            # get contrast-to-noise ratio (CNR) for each hemisphere
            try:
                df_cnr = _run_mri_cnr(
                    surf_dir=subjects_dir_path / subject / "surf",
                    vol_paths=[
                        subjects_dir_path / subject / vol_path
                        for vol_path in cnr_vol_paths
                    ],
                    out_path=Path(tmpdir) / f"{subject}_cnr.txt",
                    container_command_and_args=container_command_and_args,
                    verbose=verbose,
                )
            except subprocess.CalledProcessError:
                print(f"\tError calculating CNR for {subject}.")
                continue

            for col in cnr_cols:
                for index in df_cnr.index:
                    fname, hemi = index
                    data_subject[f"{col}-{fname.replace('.', '_')}-{hemi}"] = (
                        df_cnr.loc[[index], col].item()
                    )

            data_for_df.append(data_subject)

    df_qc = pd.DataFrame(data_for_df).set_index(sub_colname)

    return df_qc


def run_single(
    subjects_dir_path: Union[str, os.PathLike],
    container_command_and_args: Optional[list[str]] = None,
    aseg_measures: list[str] = DEFAULT_ASEG_MEASURES,
    aparc_parcellations: list[str] = DEFAULT_APARC_PARCELLATIONS,
    aparc_measures: list[str] = DEFAULT_APARC_MEASURES,
    aseg_optional_args: Optional[list[str]] = None,
    aparc_optional_args: Optional[list[str]] = None,
    with_qc: bool = False,
    euler_surf_paths: list[Union[str, os.PathLike]] = DEFAULT_EULER_SURF_PATHS,
    cnr_vol_paths: list[Union[str, os.PathLike]] = DEFAULT_CNR_VOL_PATHS,
    cnr_cols: list[str] = DEFAULT_CNR_COLS,
    sub_colname: str = DEFAULT_SUB_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
    verbose: bool = False,
) -> tuple[pd.DataFrame, Optional[pd.DataFrame]]:
    """Extract FreeSurfer aseg/aparc statistics and QC metrics for a single session.

    Parameters
    ----------
    subjects_dir_path : Union[str, os.PathLike]
        Path to the FreeSurfer subjects directory.
    container_command_and_args : Optional[list[str]], optional
        Passed to run_single_stats and run_single_qc.
    aseg_measures : list[str]
        List of measures to use for aparcstats2table.
    aparc_parcellations : list[str]
        List of parcellations to use for asegstats2table.
    aparc_measures : list[str]
        List of measures to use for asegstats2table.
    aseg_optional_args : Optional[list[str]], optional
        Passed to run_single_stats.
    aparc_optional_args : Optional[list[str]], optional
        Passed to run_single_stats.
    with_qc : bool, optional
        Whether or not to include QC metrics.
    euler_surf_paths : list[Union[str, os.PathLike]], optional
        Passed to run_single_qc.
    cnr_vol_paths : list[Union[str, os.PathLike]], optional
        Passed to run_single_qc.
    cnr_cols : list[str], optional
        Passed to run_single_qc.
    sub_colname : str, optional
        Passed to run_single_stats and run_single_qc.
    sub_prefix : str, optional
        Passed to run_single_stats and run_single_qc.
    verbose : bool, optional
        Passed to run_single_stats and run_single_qc.

    Returns
    -------
    tuple[pd.DataFrame, Optional[pd.DataFrame]]
        DataFrames with multi-level index (subject, session) and FreeSurfer stats
        columns. Second "dataframe" is None if with_qc is False.
    """
    subjects_dir_path = Path(subjects_dir_path).resolve()

    dfs_aseg = run_single_aseg(
        subjects_dir_path=subjects_dir_path,
        container_command_and_args=container_command_and_args,
        measures=aseg_measures,
        optional_args=aseg_optional_args,
        sub_colname=sub_colname,
        sub_prefix=sub_prefix,
        verbose=verbose,
    )

    dfs_aparc = run_single_aparc(
        subjects_dir_path=subjects_dir_path,
        container_command_and_args=container_command_and_args,
        parcellations=aparc_parcellations,
        measures=aparc_measures,
        optional_args=aparc_optional_args,
        sub_colname=sub_colname,
        sub_prefix=sub_prefix,
        verbose=verbose,
    )

    if with_qc:
        df_qc = run_single_qc(
            subjects_dir_path=subjects_dir_path,
            euler_surf_paths=euler_surf_paths,
            cnr_vol_paths=cnr_vol_paths,
            cnr_cols=cnr_cols,
            container_command_and_args=container_command_and_args,
            sub_colname=sub_colname,
            sub_prefix=sub_prefix,
            verbose=verbose,
        )
    else:
        df_qc = None

    return dfs_aseg, dfs_aparc, df_qc


def run_multi(
    sessions_dir_path: Union[str, os.PathLike],
    container_command_and_args: Optional[list[str]] = None,
    aseg_measures: list[str] = DEFAULT_ASEG_MEASURES,
    aparc_parcellations: list[str] = DEFAULT_APARC_PARCELLATIONS,
    aparc_measures: list[str] = DEFAULT_APARC_MEASURES,
    aparc_optional_args: Optional[list[str]] = None,
    aseg_optional_args: Optional[list[str]] = None,
    with_qc: bool = False,
    euler_surf_paths: list[Union[str, os.PathLike]] = DEFAULT_EULER_SURF_PATHS,
    cnr_vol_paths: list[Union[str, os.PathLike]] = DEFAULT_CNR_VOL_PATHS,
    cnr_cols: list[str] = DEFAULT_CNR_COLS,
    sub_colname: str = DEFAULT_SUB_COLNAME,
    ses_colname: str = DEFAULT_SES_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
    ses_prefix: str = DEFAULT_SES_PREFIX,
    verbose: bool = False,
) -> tuple[pd.DataFrame, Optional[pd.DataFrame]]:
    """Extract FreeSurfer aseg/aparc statistics and QC metrics for multiple sessions.

    This function calls run_single for each session and concatenates the results
    with a session level in the index.

    Parameters
    ----------
    sessions_dir_path : Union[str, os.PathLike]
        Path containing multiple FreeSurfer subjects directories, one for each session.
    aseg_measures : list[str]
        List of measures to use for aparcstats2table.
    aparc_parcellations : list[str]
        List of parcellations to use for asegstats2table.
    aparc_measures : list[str]
        List of measures to use for asegstats2table.
    container_command_and_args : Optional[list[str]], optional
        Passed to run_single.
    aparc_optional_args : Optional[list[str]], optional
        Passed to run_single.
    aseg_optional_args : Optional[list[str]], optional
        Passed to run_single.
    with_qc : bool, optional
        Whether or not to include QC metrics.
    euler_surf_paths : list[Union[str, os.PathLike]], optional
        Passed to run_single.
    cnr_vol_paths : list[Union[str, os.PathLike]], optional
        Passed to run_single.
    cnr_cols : list[str], optional
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
    tuple[pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame]]
        Dataframes with multi-level index (subject, session) and FreeSurfer stats
        columns. First dataframe is for aseg and second is for aparc. Third
        "dataframe" is None if with_qc is False.
    """
    sessions_dir_path = Path(sessions_dir_path)

    # get a dataframe for each session
    session_df_map_aseg = defaultdict(dict)  # {key: {session_id: df}}
    session_df_map_aparc = defaultdict(dict)  # {key: {session_id: df}}
    session_df_map_qc = {}  # {session_id: df}
    n_sessions = 0
    for dpath_session in sorted(sessions_dir_path.iterdir()):
        if not dpath_session.is_dir():
            continue

        n_sessions += 1
        session_id = dpath_session.name.removeprefix(ses_prefix)
        print(f"===== {session_id} =====")

        dfs_aseg, dfs_aparc, df_qc = run_single(
            subjects_dir_path=dpath_session,
            container_command_and_args=container_command_and_args,
            aseg_measures=aseg_measures,
            aparc_parcellations=aparc_parcellations,
            aparc_measures=aparc_measures,
            aseg_optional_args=aseg_optional_args,
            aparc_optional_args=aparc_optional_args,
            with_qc=with_qc,
            euler_surf_paths=euler_surf_paths,
            cnr_vol_paths=cnr_vol_paths,
            cnr_cols=cnr_cols,
            sub_colname=sub_colname,
            sub_prefix=sub_prefix,
            verbose=verbose,
        )

        for key, df in dfs_aseg.items():
            session_df_map_aseg[key][session_id] = df
        for key, df in dfs_aparc.items():
            session_df_map_aparc[key][session_id] = df
        session_df_map_qc[session_id] = df_qc

    if n_sessions == 0:
        _print_error_and_exit(f"No session directories found in {sessions_dir_path}.")

    dfs_aseg_multi = {
        key: pd.concat(df_map, names=[ses_colname])
        for key, df_map in session_df_map_aseg.items()
    }
    dfs_aparc_multi = {
        key: pd.concat(df_map, names=[ses_colname])
        for key, df_map in session_df_map_aparc.items()
    }
    if with_qc:
        df_qc_multi = pd.concat(session_df_map_qc, names=[ses_colname])
    else:
        df_qc_multi = None

    return dfs_aseg_multi, dfs_aparc_multi, df_qc_multi


def run(
    input_dir_path: Union[str, os.PathLike],
    output_dir_path: Union[str, os.PathLike],
    mode: str = DEFAULT_MODE,
    with_qc: bool = False,
    container_command_and_args: Optional[list[str]] = None,
    aseg_measures: list[str] = DEFAULT_ASEG_MEASURES,
    aparc_parcellations: list[str] = DEFAULT_APARC_PARCELLATIONS,
    aparc_measures: list[str] = DEFAULT_APARC_MEASURES,
    aparc_optional_args: Optional[list[str]] = None,
    aseg_optional_args: Optional[list[str]] = None,
    euler_surf_paths: list[Union[str, os.PathLike]] = DEFAULT_EULER_SURF_PATHS,
    cnr_vol_paths: list[Union[str, os.PathLike]] = DEFAULT_CNR_VOL_PATHS,
    cnr_cols: list[str] = DEFAULT_CNR_COLS,
    sub_colname: str = DEFAULT_SUB_COLNAME,
    ses_colname: str = DEFAULT_SES_COLNAME,
    sub_prefix: str = DEFAULT_SUB_PREFIX,
    ses_prefix: str = DEFAULT_SES_PREFIX,
    verbose: bool = False,
):
    """Extract FreeSurfer aseg/aparc statistics into a single file.

    Optionally extract QC metrics into a separate file.

    This extractor uses FreeSurfer commands (asegstats2table, aparcstats2table,
    mris_euler_number, and mri_cnr), and so requires FreeSurfer installation or
    a container with FreeSurfer available.

    Parameters
    ----------
    input_dir_path : Union[str, os.PathLike]
        Path to input directory, which should be a FreeSurfer subjects directory if
        mode is "single" or a directory containing multiple FreeSurfer subjects
        directories if mode is "multi".
    output_dir_path : Union[str, os.PathLike]
        Path to the directory where output files will be created. Any existing file
        may be overwritten.
    aseg_measures : list[str]
        List of measures to use for aparcstats2table.
    aparc_parcellations : list[str]
        List of parcellations to use for asegstats2table.
    aparc_measures : list[str]
        List of measures to use for asegstats2table.
    with_qc : bool, optional
        Whether or not to compute QC metrics.
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
        Optional arguments to pass to aparcstats2table, by default None. Should
        not include --subjects, --tablefile (or -t), --hemo, --measure or --parc
        arguments.
    aseg_optional_args : Optional[list[str]], optional
        Optional arguments to pass to asegstats2table, by default None. Should
        not include --subjects, --tablefile or --meas argument.
    euler_surf_paths : list[Union[str, os.PathLike]], optional
        Paths to surface files for which to calculate number of holes with
        mris_euler_number.
    cnr_vol_paths : list[Union[str, os.PathLike]], optional
        Paths to volume files for which to calculate contrast-to-noise ratios
        with mri_cnr.
    cnr_cols : list[str], optional
        Metrics to extract from mri_cnr outputs.
    sub_colname : str, optional
        Column name to use for the subject ID in the final output files.
    ses_colname : str, optional
        Column name to use for the session ID in the final output files.
    sub_prefix : str, optional
        Prefix to strip from the subject IDs in the final output files.
        Set as empty string to keep the original values.
    ses_prefix : str, optional
        Prefix to strip from the session IDs in the final output files.
        Set as empty string to keep the original values.
    """
    # single subjects directory (no sessions)
    if mode == MODE_SINGLE:
        dfs_aseg, dfs_aparc, df_qc = run_single(
            subjects_dir_path=input_dir_path,
            aseg_measures=aseg_measures,
            aparc_parcellations=aparc_parcellations,
            aparc_measures=aparc_measures,
            aseg_optional_args=aseg_optional_args,
            aparc_optional_args=aparc_optional_args,
            container_command_and_args=container_command_and_args,
            with_qc=with_qc,
            euler_surf_paths=euler_surf_paths,
            cnr_vol_paths=cnr_vol_paths,
            cnr_cols=cnr_cols,
            sub_colname=sub_colname,
            sub_prefix=sub_prefix,
            verbose=verbose,
        )

    # multiple subjects directories (assumed to be sessions)
    elif mode == MODE_MULTI:
        dfs_aseg, dfs_aparc, df_qc = run_multi(
            sessions_dir_path=input_dir_path,
            aseg_measures=aseg_measures,
            aparc_parcellations=aparc_parcellations,
            aparc_measures=aparc_measures,
            aseg_optional_args=aseg_optional_args,
            aparc_optional_args=aparc_optional_args,
            container_command_and_args=container_command_and_args,
            with_qc=with_qc,
            euler_surf_paths=euler_surf_paths,
            cnr_vol_paths=cnr_vol_paths,
            cnr_cols=cnr_cols,
            sub_colname=sub_colname,
            sub_prefix=sub_prefix,
            ses_colname=ses_colname,
            ses_prefix=ses_prefix,
            verbose=verbose,
        )

    else:
        _print_error_and_exit(
            f"Invalid mode: {mode}. Must be one of: {MODE_SINGLE}, {MODE_MULTI}"
        )

    # output directory
    output_dir_path = Path(output_dir_path)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    # get FreeSurfer version number, to prepend to output file names
    fs_version = _get_fs_version(
        input_dir_path, fname_version=FNAME_FS_VERSION, re_version=RE_FS_VERSION
    )
    if fs_version is not None:
        prefix = f"fs{fs_version}-"
    else:
        prefix = ""

    for measure, df_aseg in dfs_aseg.items():
        fpath_aseg = output_dir_path / f"{prefix}aseg-{measure}.tsv"
        df_aseg.to_csv(fpath_aseg, sep="\t")
        print(
            "\nSaved aggregated aseg stats file with shape "
            f"{df_aseg.shape} to {fpath_aseg}."
        )

    for (parcellation, measure), df_aparc in dfs_aparc.items():
        fpath_aparc = output_dir_path / f"{prefix}{parcellation}-{measure}.tsv"
        df_aparc.to_csv(fpath_aparc, sep="\t")
        print(
            "Saved aggregated aparc stats file with shape "
            f"{df_aparc.shape} to {fpath_aparc}."
        )

    if with_qc:
        fpath_qc = output_dir_path / f"{prefix}qc.tsv"
        df_qc.to_csv(fpath_qc, sep="\t")
        print(
            f"Saved aggregated QC metrics file with shape {df_qc.shape} to {fpath_qc}."
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
        "output_dir_path",
        type=Path,
        help="Path to the output directory.",
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
        "--with-qc",
        action="store_true",
        default=False,
        help="Whether to compute QC metrics and save them to a separate file.",
    )
    parser.add_argument(
        "--aseg-measures",
        type=str,
        nargs="+",
        default=DEFAULT_ASEG_MEASURES,
        help=(
            "List of measures to use for asegstats2table."
            f" Default: {DEFAULT_ASEG_MEASURES}."
        ),
    )
    parser.add_argument(
        "--aparc-parcellations",
        type=str,
        nargs="+",
        default=DEFAULT_APARC_PARCELLATIONS,
        help=(
            "List of parcellations to use for aparcstats2table (minus 'aparc.' prefix)."
            f" Default: {DEFAULT_APARC_PARCELLATIONS}."
        ),
    )
    parser.add_argument(
        "--aparc-measures",
        type=str,
        nargs="+",
        default=DEFAULT_APARC_MEASURES,
        help=(
            "List of measure to use for aparcstats2table. Default: "
            f"{DEFAULT_APARC_MEASURES}."
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
        help=(
            "Optional arguments to pass to asegstats2table, as a single string."
            " Should not include --subjects, --tablefile or --meas arguments."
        ),
    )
    parser.add_argument(
        "--aparc-args",
        type=str,
        default="",
        help=(
            "Optional arguments to pass to aparcstats2table, as a single string."
            " Should not include --subjects, --tablefile (or -t), --hemi, --measure or "
            "--parc arguments."
        ),
    )
    parser.add_argument(
        "--euler-surf-paths",
        nargs="+",
        type=Path,
        default=DEFAULT_EULER_SURF_PATHS,
        help=(
            "Paths to the surface files to calculate the Euler number from "
            f"(default: {[str(path) for path in DEFAULT_EULER_SURF_PATHS]})."
        ),
    )
    parser.add_argument(
        "--cnr-vol-paths",
        nargs="+",
        type=Path,
        default=DEFAULT_CNR_VOL_PATHS,
        help=(
            "Paths to the volume files to calculate the contrast-to-noise ratio from "
            f"(default: {[str(path) for path in DEFAULT_CNR_VOL_PATHS]})."
        ),
    )
    parser.add_argument(
        "--cnr-measures",
        nargs="+",
        default=DEFAULT_CNR_COLS,
        choices=ALL_CNR_COLS,
        help=(
            "Names of the CNR measures to include in the QC metrics file "
            f"for each volume (default: {DEFAULT_CNR_COLS})."
        ),
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
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print more information during execution.",
    )
    return parser


if __name__ == "__main__":

    parser = build_parser()
    args = parser.parse_args()
    run(
        input_dir_path=args.input_dir_path,
        output_dir_path=args.output_dir_path,
        mode=args.mode,
        aseg_measures=args.aseg_measures,
        aparc_parcellations=args.aparc_parcellations,
        aparc_measures=args.aparc_measures,
        with_qc=args.with_qc,
        container_command_and_args=shlex.split(args.container),
        aseg_optional_args=shlex.split(args.aseg_args),
        aparc_optional_args=shlex.split(args.aparc_args),
        euler_surf_paths=args.euler_surf_paths,
        cnr_vol_paths=args.cnr_vol_paths,
        cnr_cols=args.cnr_measures,
        sub_colname=args.sub_colname,
        ses_colname=args.ses_colname,
        sub_prefix=args.sub_prefix,
        ses_prefix=args.ses_prefix,
        verbose=args.verbose,
    )
