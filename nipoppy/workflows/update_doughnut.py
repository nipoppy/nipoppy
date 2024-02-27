"""Workflow for init command."""

from pathlib import Path

from nipoppy.models.doughnut import Doughnut
from nipoppy.utils import participant_id_to_bids_id, participant_id_to_dicom_id
from nipoppy.workflows.workflow import _Workflow


class UpdateDoughnut(_Workflow):
    """Workflow for creating/updating a dataset's doughnut file."""

    def __init__(self, dpath_root: Path, empty=False, regenerate=False, **kwargs):
        """Initialize the workflow."""
        super().__init__(dpath_root=dpath_root, name="doughnut", **kwargs)

        self.empty = empty
        self.regenerate = regenerate

    def run_main(self):
        """Update exiting doughnut file and/or generate a new one."""
        self.update_doughnut(empty=self.empty)

    def generate_doughnut(self, empty=False) -> Doughnut:
        """Generate a doughnut object."""

        def check_status(
            dpath: str | Path,
            participant_dname: str,
            session: str,
            session_first=False,
        ):
            dpath = Path(dpath)
            if session_first:
                dpath_participant = dpath / session / participant_dname
            else:
                dpath_participant = dpath / participant_dname / session
            if dpath_participant.exists():
                return not (next(dpath_participant.iterdir(), None) is None)
            return False

        manifest = self.manifest
        # TODO log some messages

        doughnut_records = []

        # TODO load custom ID map

        # get participants/sessions with imaging data
        for _, record in manifest.get_imaging_only().iterrows():
            participant = record[self.manifest.col_participant_id]
            session = record[self.manifest.col_session]
            # datatype = record[self.manifest.col_datatype]

            # if len(record) == 0:
            #     self.logger.warning(
            #         f"No datatypes specified in the manifest for record {record}"
            #     )

            # get DICOM dir
            # TODO allow custom map
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
                    self.layout.dpath_raw_dicom,
                    participant_dicom_dir,
                    session,
                    session_first=True,
                )
                status_organized = check_status(
                    self.layout.dpath_dicom,
                    dicom_id,
                    session,
                    session_first=True,
                )
                status_converted = check_status(
                    self.layout.dpath_bids,
                    bids_id,
                    session,
                    session_first=False,
                )

            doughnut_records.append(
                {
                    Doughnut.col_participant_id: participant,
                    Doughnut.col_session: session,
                    Doughnut.col_participant_dicom_dir: participant_dicom_dir,
                    Doughnut.col_dicom_id: dicom_id,
                    Doughnut.col_bids_id: bids_id,
                    Doughnut.col_downloaded: status_downloaded,
                    Doughnut.col_organized: status_organized,
                    Doughnut.col_converted: status_converted,
                }
            )

        doughnut = Doughnut(doughnut_records)
        return doughnut

    def update_doughnut(self, empty=False) -> Doughnut:
        """Update an existing doughnut file."""
        # get existing doughnut
        # set null if it doesn't exist
        # compare with manifest
        # update doughnut (add records)
        # save
        pass
