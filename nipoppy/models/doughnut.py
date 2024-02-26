"""Class for the doughnut file."""

from nipoppy.models.tabular import _Tabular, _TabularModel


class Doughnut(_Tabular):
    """A dataset's doughnut, for tracking DICOM-to-BIDS conversion status."""

    # column names
    col_participant_id = "participant_id"
    col_session = "session"
    col_participant_dicom_dir = "participant_dicom_dir"
    col_dicom_id = "dicom_id"
    col_bids_id = "bids_id"
    col_downloaded = "downloaded"
    col_organized = "organized"
    col_converted = "converted"

    sort_cols = [col_participant_id, col_session]

    class DoughnutModel(_TabularModel):
        """Model for the doughnut file."""

        participant_id: str
        session: str
        participant_dicom_dir: str
        dicom_id: str
        bids_id: str
        downloaded: bool
        organized: bool
        converted: bool

    # set the model
    model = DoughnutModel
