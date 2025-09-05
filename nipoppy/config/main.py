"""Dataset configuration."""

from __future__ import annotations

import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

from nipoppy.config.container import _SchemaWithContainerConfig
from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.env import PipelineTypeEnum, StrOrPathLike
from nipoppy.layout import DEFAULT_LAYOUT_INFO
from nipoppy.tabular.dicom_dir_map import DicomDirMap
from nipoppy.utils import apply_substitutions_to_json, load_json


class PipelineVariables(BaseModel):
    """Schema for pipeline variables in main config."""

    _pipeline_type_to_key = {
        PipelineTypeEnum.BIDSIFICATION: "BIDSIFICATION",
        PipelineTypeEnum.PROCESSING: "PROCESSING",
        PipelineTypeEnum.EXTRACTION: "EXTRACTION",
    }

    BIDSIFICATION: dict[str, dict[str, dict[str, Optional[str]]]] = Field(
        default_factory=(lambda: defaultdict(lambda: defaultdict(dict))),
        description=(
            "Variables for the BIDSification pipelines. This should be a nested "
            "dictionary with these levels: "
            "pipeline name -> pipeline version -> variable name -> variable value"
        ),
    )
    PROCESSING: dict[str, dict[str, dict[str, Optional[str]]]] = Field(
        default_factory=(lambda: defaultdict(lambda: defaultdict(dict))),
        description=(
            "Variables for the processing pipelines. This should be a nested "
            "dictionary with these levels: "
            "pipeline name -> pipeline version -> variable name -> variable value"
        ),
    )
    EXTRACTION: dict[str, dict[str, dict[str, Optional[str]]]] = Field(
        default_factory=(lambda: defaultdict(lambda: defaultdict(dict))),
        description=(
            "Variables for the extraction pipelines. This should be a nested "
            "dictionary with these levels: "
            "pipeline name -> pipeline version -> variable name -> variable value"
        ),
    )

    model_config = ConfigDict(extra="forbid")

    def get_variables(
        self, pipeline_type: PipelineTypeEnum, pipeline_name: str, pipeline_version: str
    ) -> dict[str, str]:
        """Get the variables for a specific pipeline."""
        try:
            key = self._pipeline_type_to_key[pipeline_type]
        except KeyError:
            raise ValueError(
                f"Invalid pipeline type: {pipeline_type}. Must be an enum and one of "
                f"{self._pipeline_type_to_key.keys()}"
            )

        return getattr(self, key)[pipeline_name][pipeline_version]

    def set_variables(
        self,
        pipeline_type: PipelineTypeEnum,
        pipeline_name: str,
        pipeline_version: str,
        variables: dict[str, Optional[str]],
    ) -> Self:
        """Set the variables for a specific pipeline."""
        try:
            key = self._pipeline_type_to_key[pipeline_type]
        except KeyError:
            raise ValueError(
                f"Invalid pipeline type: {pipeline_type}. Must be an enum and one of "
                f"{self._pipeline_type_to_key.keys()}"
            )

        pipeline_variables = getattr(self, key)
        pipeline_variables[pipeline_name][pipeline_version] = variables
        setattr(self, key, pipeline_variables)

        return self

    @model_validator(mode="after")
    def validate_after(self):
        """Convert fields to defaultdicts."""
        for pipeline_type_field in self._pipeline_type_to_key.values():
            original_nested_dict = getattr(self, pipeline_type_field)
            new_nested_dict = PipelineVariables.model_fields[
                pipeline_type_field
            ].default_factory()
            for pipeline_name in original_nested_dict:
                for pipeline_version in original_nested_dict[pipeline_name]:
                    new_nested_dict[pipeline_name][pipeline_version] = (
                        original_nested_dict[pipeline_name][pipeline_version]
                    )
            setattr(self, pipeline_type_field, new_nested_dict)

        return self


class Config(_SchemaWithContainerConfig):
    """Schema for dataset configuration."""

    HPC_PREAMBLE: list[str] = Field(
        default=[],
        description=(
            "Optional string (or list of strings) for HPC setup, including job "
            "scheduler directives or environment initialization. Examples: loading "
            "modules (e.g., Apptainer/Singularity), activating a Python environment "
            "with Nipoppy installed, and setting up job-specific variables."
        ),
    )
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
    PIPELINE_VARIABLES: PipelineVariables = Field(
        default=PipelineVariables(),
        description=(
            "Pipeline-specific variables. Typically these are paths to external "
            "resources needed by a pipeline that need to be provided by the user"
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

    def _check_substitutions(self) -> Self:
        """Check that substitutions do not have empty keys."""
        for key, value in self.SUBSTITUTIONS.items():
            if not key:
                raise ValueError("Substitutions cannot have empty keys")

            if value != (value_stripped := value.strip()):
                warnings.warn(
                    (
                        f"Substitution value for key '{key}' has leading/trailing "
                        f"whitespace: '{value}'. Stripping it."
                    ),
                    UserWarning,
                )
                self.SUBSTITUTIONS[key] = value_stripped

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
        - Convert HPC_PREAMBLE to list of strings if needed
        """
        deprecated_keys = ["DATASET_NAME", "VISIT_IDS", "SESSION_IDS"]
        key_hpc_preamble = "HPC_PREAMBLE"
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
            if isinstance(data.get(key_hpc_preamble), str):
                data[key_hpc_preamble] = [data[key_hpc_preamble]]
        return data

    @model_validator(mode="after")
    def validate_and_process(self) -> Self:
        """Validate and process the configuration."""
        self._check_dicom_dir_options()
        self._check_substitutions()

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

    def apply_pipeline_variables(
        self,
        pipeline_type: PipelineTypeEnum,
        pipeline_name: str,
        pipeline_version: str,
        json_obj: dict | list,
    ) -> dict | list:
        """Apply pipeline-specific variables to a JSON object."""
        pipeline_variables = {
            f"[[{key}]]": value
            for key, value in self.PIPELINE_VARIABLES.get_variables(
                pipeline_type, pipeline_name, pipeline_version
            ).items()
        }
        return apply_substitutions_to_json(json_obj, pipeline_variables)

    @classmethod
    def load(cls, path: StrOrPathLike, apply_substitutions=True) -> Self:
        """Load a dataset configuration from a file."""
        substitutions_key = "SUBSTITUTIONS"
        config_dict = load_json(path)
        substitutions = config_dict.get(substitutions_key, {})
        if apply_substitutions and substitutions:
            # apply user-defined substitutions to all fields except SUBSTITUTIONS itself
            config_dict = apply_substitutions_to_json(config_dict, substitutions)
            config_dict[substitutions_key] = substitutions
        config = cls(**config_dict)
        return config
