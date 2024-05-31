"""Dataset configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from pydantic import ConfigDict, Field, model_validator
from typing_extensions import Self

from nipoppy.config.container import ModelWithContainerConfig
from nipoppy.config.pipeline import PipelineConfig
from nipoppy.layout import DEFAULT_LAYOUT_INFO
from nipoppy.tabular.dicom_dir_map import DicomDirMap
from nipoppy.utils import (
    BIDS_SESSION_PREFIX,
    StrOrPathLike,
    check_session,
    check_session_strict,
    load_json,
)


class Config(ModelWithContainerConfig):
    """Model for dataset configuration."""

    DATASET_NAME: str = Field(description="Name of the dataset")
    VISITS: list[str] = Field(description="List of visits available in the study")
    SESSIONS: Optional[list[str]] = Field(
        default=None,  # will be a list after validation
        description=(
            "List of BIDS-compliant sessions available in the study"
            f', prefixed with "{BIDS_SESSION_PREFIX}"'
            " (inferred from VISITS if not given)"
        ),
    )
    DICOM_DIR_MAP_FILE: Optional[Path] = Field(
        default=None,
        description=(
            "Path to a CSV file mapping participant IDs to DICOM directories"
            ", to be used in the DICOM reorg step. Note: this field and "
            "DICOM_DIR_PARTICIPANT_FIRST cannot both be specified"
            f'. The CSV should have three columns: "{DicomDirMap.col_participant_id}"'
            f' , "{DicomDirMap.col_session}"'
            f', and "{DicomDirMap.col_participant_dicom_dir}"'
        ),
    )
    DICOM_DIR_PARTICIPANT_FIRST: Optional[bool] = Field(
        default=None,
        description=(
            "Whether subdirectories under the raw dicom directory (default: "
            f"{DEFAULT_LAYOUT_INFO.dpath_raw_dicom}) follow the pattern "
            "<PARTICIPANT>/<SESSION> (default) or <SESSION>/<PARTICIPANT>. Note: "
            "this field and and DICOM_DIR_MAP_FILE cannot both be specified"
        ),
    )
    BIDS: dict[str, dict[str, dict[str, PipelineConfig]]] = Field(
        default={}, description="Configurations for BIDS converters, if any"
    )
    PROC_PIPELINES: dict[str, dict[str, PipelineConfig]] = Field(
        description="Configurations for processing pipelines"
    )

    model_config = ConfigDict(extra="allow")

    def _check_sessions_have_prefix(self) -> Self:
        """Check that sessions have the BIDS prefix."""
        for session in self.SESSIONS:
            check_session_strict(session)
        return self

    def _check_dicom_dir_options(self) -> Self:
        """Check that only one DICOM directory mapping option is given."""
        if (
            self.DICOM_DIR_MAP_FILE is not None
            and self.DICOM_DIR_PARTICIPANT_FIRST is not None
        ):
            raise ValueError(
                "Cannot specify both DICOM_DIR_MAP_FILE and DICOM_DIR_PARTICIPANT_FIRST"
            )
        # otherwise set the default if needed
        elif self.DICOM_DIR_PARTICIPANT_FIRST is None:
            self.DICOM_DIR_PARTICIPANT_FIRST = True

        return self

    def _check_no_duplicate_pipeline(self) -> Self:
        """Check that BIDS and PROC_PIPELINES do not have common pipelines."""
        bids_pipelines = set(self.BIDS.keys())
        proc_pipelines = set(self.PROC_PIPELINES.keys())
        if len(bids_pipelines & proc_pipelines) != 0:
            raise ValueError(
                "Cannot have the same pipeline under BIDS and PROC_PIPELINES"
                f", got {bids_pipelines} and {proc_pipelines}"
            )
        return self

    def _propagate_container_config(self) -> Self:
        """Propagate the container config to all pipelines."""

        def _propagate(pipeline_or_pipeline_dicts: dict | PipelineConfig):
            if isinstance(pipeline_or_pipeline_dicts, PipelineConfig):
                pipeline_config = pipeline_or_pipeline_dicts
                container_config = pipeline_config.get_container_config()
                if container_config.INHERIT:
                    container_config.merge_args_and_env_vars(self.CONTAINER_CONFIG)
            else:
                for (
                    child_pipeline_or_pipeline_dicts
                ) in pipeline_or_pipeline_dicts.values():
                    _propagate(child_pipeline_or_pipeline_dicts)

        _propagate(self.BIDS)
        _propagate(self.PROC_PIPELINES)

        return self

    @model_validator(mode="before")
    @classmethod
    def check_input(cls, data: Any):
        """Validate the raw input."""
        key_sessions = "SESSIONS"
        key_visits = "VISITS"
        if isinstance(data, dict):
            # if sessions are not given, infer from visits
            if key_sessions not in data:
                data[key_sessions] = [
                    check_session(visit) for visit in data[key_visits]
                ]

        return data

    @model_validator(mode="after")
    def validate_and_process(self) -> Self:
        """Validate and process the configuration."""
        self._check_sessions_have_prefix()
        self._check_dicom_dir_options()
        self._check_no_duplicate_pipeline()
        self._propagate_container_config()
        return self

    def get_pipeline_config(
        self,
        pipeline_name: str,
        pipeline_version: str,
    ) -> PipelineConfig:
        """Get the config for a pipeline."""
        try:
            return self.PROC_PIPELINES[pipeline_name][pipeline_version]
        except KeyError:
            raise ValueError(f"No config found for {pipeline_name} {pipeline_version}")

    def get_bids_pipeline_config(
        self, pipeline_name: str, pipeline_version: str, pipeline_step: str
    ) -> PipelineConfig:
        """Get the config for a BIDS conversion pipeline."""
        try:
            return self.BIDS[pipeline_name][pipeline_version][pipeline_step]
        except KeyError:
            raise ValueError(
                "No config found for "
                f"{pipeline_name} {pipeline_version} {pipeline_step}"
            )

    def save(self, fpath: StrOrPathLike, **kwargs):
        """Save the config to a JSON file.

        Parameters
        ----------
        fpath : nipoppy.utils.StrOrPathLike
            Path to the JSON file to write
        """
        fpath = Path(fpath)
        if "indent" not in kwargs:
            kwargs["indent"] = 4
        fpath.parent.mkdir(parents=True, exist_ok=True)
        with open(fpath, "w") as file:
            file.write(self.model_dump_json(**kwargs))

    @classmethod
    def load(cls, path: StrOrPathLike) -> Self:
        """Load a dataset configuration."""
        return cls(**load_json(path))
