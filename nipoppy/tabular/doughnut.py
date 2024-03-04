"""Class for the doughnut file."""

import logging
from pathlib import Path
from typing import Optional

from nipoppy.logger import get_logger
from nipoppy.tabular.manifest import Manifest
from nipoppy.utils import participant_id_to_bids_id, participant_id_to_dicom_id


class Doughnut(Manifest):
    """A dataset's doughnut, for tracking DICOM-to-BIDS conversion status."""

    # column names
    col_participant_dicom_dir = "participant_dicom_dir"
    col_dicom_id = "dicom_id"
    col_bids_id = "bids_id"
    col_downloaded = "downloaded"
    col_organized = "organized"
    col_converted = "converted"

    class DoughnutModel(Manifest.ManifestModel):
        """Model for the doughnut file."""

        participant_dicom_dir: str
        dicom_id: str
        bids_id: str
        downloaded: bool
        organized: bool
        converted: bool

    # set the model
    model = DoughnutModel

    index_cols = [Manifest.col_participant_id, Manifest.col_session]


def generate_doughnut(
    manifest: Manifest,
    dpath_downloaded: Optional[str | Path] = None,
    dpath_organized: Optional[str | Path] = None,
    dpath_converted: Optional[str | Path] = None,
    empty=False,
    logger: Optional[logging.Logger] = None,
    # TODO allow custom map from participant_id to participant_dicom_dir
) -> Doughnut:
    """Generate a doughnut object."""

    def check_status(
        dpath: Optional[str | Path],
        participant_dname: str,
        session: str,
        session_first=False,
    ):
        if dpath is None:
            status = False
        else:
            dpath = Path(dpath)
            if session_first:
                dpath_participant = dpath / session / participant_dname
            else:
                dpath_participant = dpath / participant_dname / session
            if dpath_participant.exists():
                status = not (next(dpath_participant.iterdir(), None) is None)
            else:
                status = False
            logger.debug(f"Status for {dpath_participant}: {status}")
        return status

    if logger is None:
        logger = get_logger("generate_doughnut")

    # get participants/sessions with imaging data
    logger.debug(f"Full manifest:\n{manifest}")
    manifest_imaging_only = manifest.get_imaging_only()
    logger.debug(f"Imaging-only manifest:\n{manifest_imaging_only}")

    doughnut_records = []
    for _, manifest_record in manifest_imaging_only.iterrows():
        participant = manifest_record[manifest.col_participant_id]
        session = manifest_record[manifest.col_session]

        # get DICOM dir
        participant_dicom_dir = participant

        # get DICOM and BIDS IDs
        dicom_id = participant_id_to_dicom_id(participant)
        bids_id = participant_id_to_bids_id(participant)

        if empty:
            status_downloaded = False
            status_organized = False
            status_converted = False
        else:
            status_downloaded = check_status(
                dpath_downloaded,
                participant_dicom_dir,
                session,
                session_first=True,
            )
            status_organized = check_status(
                dpath_organized,
                dicom_id,
                session,
                session_first=True,
            )
            status_converted = check_status(
                dpath_converted,
                bids_id,
                session,
                session_first=False,
            )

        doughnut_records.append(
            {
                Doughnut.col_participant_id: participant,
                Doughnut.col_visit: manifest_record[Manifest.col_visit],
                Doughnut.col_session: session,
                Doughnut.col_datatype: manifest_record[Manifest.col_datatype],
                Doughnut.col_participant_dicom_dir: participant_dicom_dir,
                Doughnut.col_dicom_id: dicom_id,
                Doughnut.col_bids_id: bids_id,
                Doughnut.col_downloaded: status_downloaded,
                Doughnut.col_organized: status_organized,
                Doughnut.col_converted: status_converted,
            }
        )

    doughnut = Doughnut(doughnut_records)
    logger.debug(f"Generated doughnut:\n{doughnut}")
    return doughnut


def update_doughnut(
    doughnut: Doughnut,
    manifest: Manifest,
    dpath_downloaded: Optional[str | Path] = None,
    dpath_organized: Optional[str | Path] = None,
    dpath_converted: Optional[str | Path] = None,
    empty=False,
    logger: Optional[logging.Logger] = None,
) -> Doughnut:
    """Update an existing doughnut file."""
    if logger is None:
        logger = get_logger("update_doughnut")

    logger.debug(f"Original doughnut:\n{doughnut}")
    logger.debug(f"Manifest:\n{manifest}")
    manifest_subset = manifest.get_diff(doughnut, cols=doughnut.index_cols)
    logger.debug(
        "Manifest subset (difference between manifest and doughnut)"
        f":\n{manifest_subset}"
    )

    updated_doughnut = doughnut.concatenate(
        generate_doughnut(
            manifest=manifest_subset,
            dpath_downloaded=dpath_downloaded,
            dpath_organized=dpath_organized,
            dpath_converted=dpath_converted,
            empty=empty,
            logger=logger,
        )
    )

    logger.debug(f"Updated doughnut:\t{updated_doughnut}")

    return updated_doughnut
