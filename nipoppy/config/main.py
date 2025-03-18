"""Dataset configuration."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Optional

from pydantic import ConfigDict, Field, model_validator
from typing_extensions import Self

from nipoppy.config.container import _SchemaWithContainerConfig
from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.env import StrOrPathLike
from nipoppy.layout import DEFAULT_LAYOUT_INFO
from nipoppy.tabular.dicom_dir_map import DicomDirMap
from nipoppy.utils import apply_substitutions_to_json, load_json


class Config(_SchemaWithContainerConfig):
    """Schema for dataset configuration."""

    DICOM_DIR_MAP_FILE: Optional[Path] = Field(
        default=None,
        description=(
            "Path to a TSV file mapping participant IDs to DICOM directories"
            ", to be used in the DICOM reorg step. Note: this field and "
            "DICOM_DIR_PARTICIPANT_FIRST cannot both be specified. The "
            f'TSV file should have three columns: "{DicomDirMap.col_participant_id}"'
            f' , "{DicomDirMap.col_session_id}"'
            f', and "{DicomDirMap.col_participant_dicom_dir}"'
        ),
    )
    DICOM_DIR_PARTICIPANT_FIRST: Optional[bool] = Field(
        default=None,
        description=(
            f"Whether subdirectories under  {DEFAULT_LAYOUT_INFO.dpath_pre_reorg}) "
            "follow the pattern <PARTICIPANT>/<SESSION> (default) or "
            "<SESSION>/<PARTICIPANT>. Note: this field and DICOM_DIR_MAP_FILE "
            "cannot both be specified"
        ),
    )
    SUBSTITUTIONS: dict[str, str] = Field(
        default={},
        description=(
            "Top-level mapping for replacing placeholder expressions in the rest "
            "of the config file. Note: the replacement only happens if the config "
            "is loaded from a file with :func:`nipoppy.config.main.Config.load`"
        ),
    )
    CUSTOM: dict = Field(
        default={},
        description="Free field that can be used for any purpose",
    )

    model_config = ConfigDict(extra="forbid")

    def _check_dicom_dir_options(self) -> Self:
        """Check that only one DICOM directory mapping option is given."""
        if (
            self.DICOM_DIR_MAP_FILE is not None
            and self.DICOM_DIR_PARTICIPANT_FIRST is not None
        ):
            raise ValueError(
                "Cannot specify both DICOM_DIR_MAP_FILE and DICOM_DIR_PARTICIPANT_FIRST"
                f". Got DICOM_DIR_MAP_FILE={self.DICOM_DIR_MAP_FILE} and "
                f"DICOM_DIR_PARTICIPANT_FIRST={self.DICOM_DIR_PARTICIPANT_FIRST}"
            )

        return self

    def propagate_container_config_to_pipeline(
        self, pipeline_config: BasePipelineConfig
    ) -> BasePipelineConfig:
        """Propagate the global container config to a pipeline config."""
        pipeline_container_config = pipeline_config.get_container_config()
        if pipeline_container_config.INHERIT:
            pipeline_container_config.merge(
                self.CONTAINER_CONFIG, overwrite_command=True
            )
        for pipeline_step in pipeline_config.STEPS:
            step_container_config = pipeline_step.get_container_config()
            if step_container_config.INHERIT:
                step_container_config.merge(
                    pipeline_container_config, overwrite_command=True
                )
        return pipeline_config

    @model_validator(mode="before")
    @classmethod
    def check_input(cls, data: Any):
        """
        Validate the raw input.

        Specifically:
        - If DATASET_NAME, VISIT_IDS, or SESSION_IDS are present, ignore them and
          emit a deprecation warning
        """
        deprecated_keys = ["DATASET_NAME", "VISIT_IDS", "SESSION_IDS"]
        if isinstance(data, dict):
            for key in deprecated_keys:
                if key in data:
                    data.pop(key)
                    warnings.warn(
                        (
                            f"Field {key} is deprecated and will cause an error to be "
                            "raised in a future version. Please remove it from your "
                            "config file."
                        ),
                        DeprecationWarning,
                    )
        return data

    @model_validator(mode="after")
    def validate_and_process(self) -> Self:
        """Validate and process the configuration."""
        self._check_dicom_dir_options()

        return self

    def save(self, fpath: StrOrPathLike, **kwargs):
        """Save the config to a JSON file.

        Parameters
        ----------
        fpath : nipoppy.env.StrOrPathLike
            Path to the JSON file to write
        """
        fpath: Path = Path(fpath)
        if "indent" not in kwargs:
            kwargs["indent"] = 4
        fpath.parent.mkdir(parents=True, exist_ok=True)
        with open(fpath, "w") as file:
            file.write(self.model_dump_json(**kwargs))

    def apply_substitutions_to_json(self, json_obj: dict | list) -> dict | list:
        """Apply substitutions to a JSON object."""
        return apply_substitutions_to_json(json_obj, self.SUBSTITUTIONS)

    @classmethod
    def load(cls, path: StrOrPathLike, apply_substitutions=True) -> Self:
        """Load a dataset configuration from a file."""
        substitutions_key = "SUBSTITUTIONS"
        config_dict = load_json(path)
        substitutions = config_dict.get(substitutions_key, {})
        if apply_substitutions and substitutions:
            # apply user-defined substitutions to all fields except SUBSTITUTIONS itself
            config = cls(**apply_substitutions_to_json(config_dict, substitutions))
            config.SUBSTITUTIONS = substitutions
        else:
            config = cls(**config_dict)

        return config
