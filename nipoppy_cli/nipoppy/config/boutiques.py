"""Boutiques configuration model and utility functions."""

from pydantic import ConfigDict

from nipoppy.config.container import ModelWithContainerConfig

BOUTIQUES_CUSTOM_KEY = "custom"  # as defined by Boutiques schema
BOUTIQUES_CONFIG_KEY = "nipoppy"


class BoutiquesConfig(ModelWithContainerConfig):
    """Model for custom configuration within a Boutiques descriptor."""

    # dpath_participant_session_result (for tarring/zipping/extracting)
    # run_on (for choosing which participants/sessions to run on)
    # bids_input (for pybids)

    model_config = ConfigDict(extra="forbid")


def get_boutiques_config_from_descriptor(descriptor: dict) -> BoutiquesConfig:
    """Return the Boutiques configuration object from a descriptor."""
    try:
        data = descriptor[BOUTIQUES_CUSTOM_KEY][BOUTIQUES_CONFIG_KEY]
    except Exception:
        raise RuntimeError(
            "The Boutiques descriptor does not have a"
            f" {BOUTIQUES_CUSTOM_KEY}/{BOUTIQUES_CONFIG_KEY} field: {descriptor}"
        )
    return BoutiquesConfig(**data)
