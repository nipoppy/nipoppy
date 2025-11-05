"""High-performance computing (HPC) job submission configuration."""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, model_validator
from typing_extensions import Self


class HpcConfig(BaseModel):
    r"""
    Schema for High-Performance Computing (HPC) system configuration.

    Key-value pairs are passed to a Jinja template for the requested HPC job queue.

    Any key can be used except for the following:
        - "queue"
        - "working_directory"
        - "command"
        - Anything that starts with "NIPOPPY\_" (reserved for internal use)

    Values are converted to strings except if they are None.
    """

    _reserved_keys: ClassVar = ["queue", "working_directory", "command"]
    _reserved_prefix: ClassVar = "NIPOPPY_"

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
            if key in self._reserved_keys or key.startswith(self._reserved_prefix):
                raise ValueError(
                    f"Reserved key {key} found in HPC configuration"
                    f". Any key is allowed except for {self._reserved_keys}"
                    f" as well as keys starting with '{self._reserved_prefix}'"
                )
            if (value is not None) and not isinstance(value, str):
                setattr(self, key, str(value))
        return self
