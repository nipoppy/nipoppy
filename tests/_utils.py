"""Utilities for testing"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import nibabel as nib
import numpy as np
from nibabel import Nifti1Image


def _default_config() -> dict[str, dict[str, list[str | int] | int]]:
    """Return a config."""
    return {
        # list of possible 'datatypes'
        "fmap": {},
        "func": {
            "suffix": ["bold", "events"],
            "tasks": ["main", "rest"],
            "runs": [2, 1],
        },
        "anat": {"suffix": ["t1w"], "runs": 2},
        "dwi": {"suffix": ["dwi"]},
        # other config 
        "timestamp_format": "%Y%m%d_%H%M%S",
        "default_nifti_ext": ".nii.gz",
        "layout": "nested", # flat or nested
        "filename_template": "$subject_$suffix_$task_$run_$timestamp",
    }


def create_fake_source_dataset(
    output_dir: Path = Path.cwd() / "sourcedata",
    subjects: str | int | list[str | int] = None,
    sessions: None | str | int | list[str | int | None] = None,
    datatypes: str | list[str] = None,
    layout: str = "nested",
    config=None,
) -> None:
    """Create a fake BIDS dataset."""

    if subjects is None:
        subjects = ["01", "02"]
    if sessions is None:
        sessions = ["01", "2"]
    if datatypes is None:
        datatypes = ["anat", "func"]
    if config is None:
        config = _default_config()

    if isinstance(subjects, (str, int)):
        subjects_to_create = [subjects]
    else:
        subjects_to_create = subjects

    if layout == "flat" or sessions is None:
        sessions_to_create = [None]
    elif isinstance(sessions, (str, int)):
        sessions_to_create = [sessions]
    else:
        sessions_to_create = sessions

    if layout == "flat":
        datatypes = ["anat", "func"]
    if isinstance(datatypes, (str)):
        datatypes = [datatypes]

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now()

    for sub_label in subjects_to_create:

        entities = {"subject": sub_label}

        timestamp = timestamp + timedelta(days=1)

        for ses_label in sessions_to_create:

            if ses_label:
                timestamp = timestamp + timedelta(days=1)
                entities["session"] = ses_label

            for datatype_ in datatypes:

                entities["datatype"] = datatype_

                for suffix_ in config[datatype_]["suffix"]:
                    entities["suffix"] = suffix_

                    if suffix_ == "events":
                        entities["extension"] = ".tsv"

                    if datatype_ in ["anat", "dwi"]:
                        for run in range(1, config[datatype_].get("runs", 1)):
                            entities["run"] = run
                            filepath = _create_file(
                                output_dir,
                                entities=entities,
                                layout=layout,
                                timestamp=timestamp,
                                config=config,
                            )

                    if datatype_ == "func":
                        for i, task in enumerate(config["func"]["tasks"]):
                            for run in range(1, config["func"]["runs"][i] + 1):
                                entities["task"] = task
                                entities["run"] = run
                                filepath = _create_file(
                                    output_dir,
                                    entities=entities,
                                    layout=layout,
                                    timestamp=timestamp,
                                    config=config,
                                )
                            # _create_sidecar(filepath)


def _rng(seed=42):
    return np.random.default_rng(seed)


def _affine_eye():
    """Return an identity matrix affine."""
    return np.eye(4)


def _shape_3d_default():
    """Return default shape for a 3D image."""
    return (10, 10, 10)


def _length_default():
    return 10


def _shape_4d_default():
    """Return default shape for a 4D image."""
    return (10, 10, 10, _length_default())


def _img_3d_rand_eye(affine=_affine_eye()):
    """Return random 3D Nifti1Image in MNI space."""
    data = _rng().random(_shape_3d_default())
    return Nifti1Image(data, affine)


def _img_4d_rand_eye(affine=_affine_eye()):
    """Return random 3D Nifti1Image in MNI space."""
    data = _rng().random(_shape_4d_default())
    return Nifti1Image(data, affine)


def _create_file(
    output_dir: Path,
    entities: dict[str, str | int],
    layout,
    timestamp,
    config=None,
) -> Path:
    """Create an dummy file."""
    if config is None:
        config = _default_config()

    timestamp = timestamp.strftime(config["timestamp_format"])

    subject = entities['subject']

    suffix = entities["suffix"]

    run = entities.get('run')

    task = entities.get('task')

    filename = config["filename_template"]
    
    for t, c in zip(["subject", "suffix", "timestamp", "run", 'task'], [subject, suffix, timestamp, run, task]):
        print(t, c)
        filename = filename.replace(f"${t}", str(c))   

    extension = entities.get('extension', config["default_nifti_ext"])
    filename += extension

    filepath = output_dir / f"sub-{entities['subject']}"
    if entities.get("session"):
        filepath = filepath / entities["session"]
    if layout != "flat":
        filepath = filepath / entities["datatype"]

    filepath = filepath / filename

    filepath.parent.mkdir(parents=True, exist_ok=True)

    if extension in [".nii", ".nii.gz"]:
        image = _img_3d_rand_eye()
        if entities["datatype"] in ["func", "dwi"]:
            image = _img_4d_rand_eye()
        nib.save(image, filepath)

    return filepath


def _create_sidecar(filepath: Path) -> None:
    """Create a sidecar JSON file."""

    metadata = {}
    with open(filepath.with_suffix(".json"), "w") as f:
        json.dump(metadata, f, indent=4)


if __name__ == "__main__":
    create_fake_source_dataset(
        output_dir=Path.cwd() / "sourcedata",
        subjects=[
            "01",
            "02",
            "PC",
            "bob",
            "aaa",
        ],
        sessions=["01", "2"],
        datatypes=["anat", "func", "dwi"],
        layout="nested",
        config=_default_config(),
    )
