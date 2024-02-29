"""Class for the doughnut file."""

from nipoppy.models.manifest import Manifest


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
