"""Utilities for tests."""

from pathlib import Path
from typing import Optional

import numpy as np

FPATH_CONFIG = "proc/global_configs.json"
FPATH_MANIFEST = "tabular/manifest.csv"
DPATH_TEST_DATA = Path(__file__).parent / "data"

ATTR_TO_DPATH_MAP = {
    "dpath_bids": "bids",
    "dpath_derivatives": "derivatives",
    "dpath_dicom": "dicom",
    "dpath_downloads": "downloads",
    "dpath_proc": "proc",
    "dpath_scratch": "scratch",
    "dpath_raw_dicom": "scratch/raw_dicom",
    "dpath_logs": "scratch/logs",
    "dpath_tabular": "tabular",
    "dpath_assessments": "tabular/assessments",
    "dpath_demographics": "tabular/demographics",
}

ATTR_TO_FPATH_MAP = {
    "fpath_config": FPATH_CONFIG,
    "fpath_manifest": FPATH_MANIFEST,
    "fpath_doughnut": "scratch/raw_dicom/doughnut.csv",
}


def _process_participants_sessions(
    participants_and_sessions: Optional[dict[str, list[str]]] = None,
    participants: Optional[list[str]] = None,
    sessions: Optional[list[str] | dict[str, list[str]]] = None,
):
    """Process participant/session arguments."""
    if participants_and_sessions is None:
        if participants is None:
            participants = ["01", "02"]
        if sessions is None:
            sessions = ["ses-BL", "ses-M12"]
        participants_and_sessions = {
            participant: sessions for participant in participants
        }
    return participants_and_sessions


def _fake_dicoms(
    dpath: str | Path,
    participants_and_sessions: Optional[dict[str, list[str]]] = None,
    participants: Optional[list[str]] = None,
    sessions: Optional[list[str]] = None,
    n_images: int = 3,
    min_n_files_per_image: int = 1,
    max_n_files_per_image: int = 5,
    min_n_subdir_levels: int = 1,
    max_n_subdir_levels: int = 2,
    participant_first: bool = False,
    max_dname_dicom: int = 1000000,
    rng_seed: int = 3791,
):
    """Generate a fake dataset with raw DICOM files."""
    participants_and_sessions = _process_participants_sessions(
        participants_and_sessions, participants, sessions
    )

    if n_images < 1:
        raise ValueError("n_images must be at least 1")
    if min_n_files_per_image < 1:
        raise ValueError("min_n_files_per_image must be at least 1")
    if max_n_files_per_image < min_n_files_per_image:
        raise ValueError("max_n_files_per_image must be at least min_n_files_per_image")
    if min_n_subdir_levels < 0:
        raise ValueError("min_n_subdir_levels must be at least 0")
    if max_n_subdir_levels < min_n_subdir_levels:
        raise ValueError("max_n_subdir_levels must be at least min_n_subdir_levels")

    rng = np.random.default_rng(rng_seed)

    dpath = Path(dpath)
    dpath.mkdir(parents=True, exist_ok=True)

    for participant, participant_sessions in participants_and_sessions.items():
        for session in participant_sessions:
            if participant_first:
                dpath_dicom_parent = dpath / participant / session
            else:
                dpath_dicom_parent = dpath / session / participant

            for i_image in range(n_images):
                n_subdir_levels = rng.integers(
                    min_n_subdir_levels, max_n_subdir_levels, endpoint=True
                )
                n_files = rng.integers(
                    min_n_files_per_image, max_n_files_per_image, endpoint=True
                )

                dpath_dicom = dpath_dicom_parent
                dnames_dicom = []
                for _ in range(n_subdir_levels):
                    dname_dicom = str(rng.integers(max_dname_dicom))
                    dpath_dicom = dpath_dicom / dname_dicom
                    dnames_dicom.append(dname_dicom)

                dpath_dicom.mkdir(parents=True, exist_ok=True)
                for i_file in range(n_files):
                    i_file_str = str(i_file).zfill(len(str(n_files)))
                    fpath_dicom = dpath_dicom / f"{i_image}-{i_file_str}.dcm"
                    fpath_dicom.touch()


def fake_dicoms_downloaded(
    dpath: str | Path,
    participants_and_sessions: Optional[dict[str, list[str]]] = None,
    participants: Optional[list[str]] = None,
    sessions: Optional[list[str]] = None,
    n_images: int = 3,
    min_n_files_per_image: int = 1,
    max_n_files_per_image: int = 5,
    min_n_subdir_levels: int = 1,
    max_n_subdir_levels: int = 2,
    participant_first: bool = False,
    max_dname_dicom: int = 1000000,
    rng_seed: int = 3791,
):
    _fake_dicoms(
        dpath=dpath,
        participants_and_sessions=participants_and_sessions,
        participants=participants,
        sessions=sessions,
        n_images=n_images,
        min_n_files_per_image=min_n_files_per_image,
        max_n_files_per_image=max_n_files_per_image,
        min_n_subdir_levels=min_n_subdir_levels,
        max_n_subdir_levels=max_n_subdir_levels,
        participant_first=participant_first,
        max_dname_dicom=max_dname_dicom,
        rng_seed=rng_seed,
    )


def fake_dicoms_organized(
    dpath: str | Path,
    participants_and_sessions: Optional[dict[str, list[str]]] = None,
    participants: Optional[list[str]] = None,
    sessions: Optional[list[str]] = None,
    n_images: int = 3,
    min_n_files_per_image: int = 1,
    max_n_files_per_image: int = 5,
    participant_first: bool = False,
    max_dname_dicom: int = 1000000,
    rng_seed: int = 3791,
):
    _fake_dicoms(
        dpath=dpath,
        participants_and_sessions=participants_and_sessions,
        participants=participants,
        sessions=sessions,
        n_images=n_images,
        min_n_files_per_image=min_n_files_per_image,
        max_n_files_per_image=max_n_files_per_image,
        min_n_subdir_levels=0,
        max_n_subdir_levels=0,
        participant_first=participant_first,
        max_dname_dicom=max_dname_dicom,
        rng_seed=rng_seed,
    )
