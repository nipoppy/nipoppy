#!/usr/bin/env python
"""Script to automatically generate JSON schema files for Pydantic models."""

import json
from pathlib import Path

from nipoppy.config.boutiques import BoutiquesConfig
from nipoppy.config.hpc import HpcConfig
from nipoppy.config.main import Config
from nipoppy.config.pipeline import (
    BidsPipelineConfig,
    ExtractionPipelineConfig,
    ProcPipelineConfig,
)
from nipoppy.config.tracker import TrackerConfig
from nipoppy.layout import LayoutConfig
from nipoppy.tabular.curation_status import CurationStatusModel
from nipoppy.tabular.dicom_dir_map import DicomDirMapModel
from nipoppy.tabular.manifest import ManifestModel
from nipoppy.tabular.processing_status import ProcessingStatusModel

DPATH_SCHEMAS = Path(__file__).parent / ".." / "source" / "schemas"

MODEL_FILENAME_MAP = {
    BoutiquesConfig: "boutiques.json",
    Config: "config.json",
    LayoutConfig: "layout.json",
    BidsPipelineConfig: "bids_pipeline.json",
    ProcPipelineConfig: "proc_pipeline.json",
    ExtractionPipelineConfig: "extraction_pipeline.json",
    HpcConfig: "hpc.json",
    TrackerConfig: "tracker.json",
    ProcessingStatusModel: "processing_status.json",
    DicomDirMapModel: "dicom_dir_map.json",
    CurationStatusModel: "curation_status.json",
    ManifestModel: "manifest.json",
}

if __name__ == "__main__":
    # make sure schemas directory exists
    if not DPATH_SCHEMAS.exists():
        print(f"\tCreating {DPATH_SCHEMAS}")
        DPATH_SCHEMAS.mkdir(parents=True)

    # generate schema files
    for model, filename in MODEL_FILENAME_MAP.items():
        print(f"\tWriting JSON schema for {model.__name__} to {filename}")
        fpath_schema = DPATH_SCHEMAS / filename

        schema = model.model_json_schema()

        # move singularity config to last property
        try:
            CONTAINER_CONFIG = schema["properties"]["CONTAINER_CONFIG"]
            del schema["properties"]["CONTAINER_CONFIG"]
            schema["properties"]["CONTAINER_CONFIG"] = CONTAINER_CONFIG
        except KeyError:
            pass

        # # TODO figure out $ref/$$target things
        # try:
        #     for subschema_name, subschema in schema["definitions"].items():
        #         pass
        # except KeyError:
        #     pass

        schema_str = json.dumps(schema, indent=4)
        fpath_schema.write_text(schema_str)
