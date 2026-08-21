#!/usr/bin/env python
"""Script to automatically generate the sample study config file shown in the docs."""

from pathlib import Path

import nipoppy.utils.fileops
from nipoppy.env import PROGRAM_VERSION
from nipoppy.utils.utils import FPATH_SAMPLE_CONFIG, TEMPLATE_PIPELINE_PATH

DPATH_INSERTS = Path(__file__).parent.parent / "source" / "_inserts"

if __name__ == "__main__":
    DPATH_INSERTS.mkdir(parents=True, exist_ok=True)

    for source, dest in [
        (FPATH_SAMPLE_CONFIG, DPATH_INSERTS / "sample_study_config.json5"),
    ] + [
        (source, DPATH_INSERTS / source.name)
        for source in TEMPLATE_PIPELINE_PATH.glob("*.json5")
    ]:
        nipoppy.utils.fileops.copy_template(
            source,
            dest,
            version=PROGRAM_VERSION,
            exist_ok=True,
        )
