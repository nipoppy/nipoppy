"""High-performance computing (HPC) job submission configuration."""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, model_validator
from typing_extensions import Self


class HpcConfig(BaseModel):
    """
    Schema for High-Performance Computing (HPC) system configuration.

    Key-value pairs are passed to a Jinja template for the requested HPC job queue.

    Any key-value pair can be used except for the following:
        - queue
        - job_name
        - dataset_root
        - command

    Values are converted to strings.
    """

    _reserved_keys: ClassVar = ["queue", "job_name", "dataset_root", "command"]

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def validate_after(self) -> Self:
        """
        Validate the HPC configuration after instantiation.

        Specifically:
        - Check that no reserved keywords are used
        - Convert all values to strings
        """
        for key, value in self.model_dump().items():
            if key in self._reserved_keys:
                raise ValueError(f"Reserved key {key} found in HPC configuration")
            if (value is not None) and not isinstance(value, str):
                setattr(self, key, str(value))
        return self
