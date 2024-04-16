#!/usr/bin/env python
"""Script to automatically generate JSON schema files for Pydantic models."""

import json
from pathlib import Path

from nipoppy.config.base import Config
from nipoppy.tabular.bagel import BagelModel
from nipoppy.tabular.doughnut import DoughnutModel
from nipoppy.tabular.manifest import ManifestModel

DPATH_SCHEMA = Path(__file__).parent / ".." / "source" / "schemas"

MODEL_FILENAME_MAP = {
    Config: "config.json",
    BagelModel: "bagel.json",
    DoughnutModel: "doughnut.json",
    ManifestModel: "manifest.json",
}

if __name__ == "__main__":
    # make sure schemas directory exists
    if not DPATH_SCHEMA.exists():
        print(f"\tCreating {DPATH_SCHEMA}")
        DPATH_SCHEMA.mkdir(parents=True)

    # generate schema files
    for model, filename in MODEL_FILENAME_MAP.items():
        print(f"\tWriting JSON schema for {model.__name__} to {filename}")
        fpath_schema = DPATH_SCHEMA / filename

        schema = model.model_json_schema()

        # move singularity config to last property
        try:
            singularity_config = schema["properties"]["SINGULARITY_CONFIG"]
            del schema["properties"]["SINGULARITY_CONFIG"]
            schema["properties"]["SINGULARITY_CONFIG"] = singularity_config
        except KeyError:
            pass

        schema_str = json.dumps(schema, indent=4)
        fpath_schema.write_text(schema_str)
