#!/usr/bin/env python

from pathlib import Path

import nipoppy.utils.fileops
from nipoppy.env import PROGRAM_VERSION
from nipoppy.utils.utils import FPATH_SAMPLE_CONFIG

DPATH_INSERTS = Path(__file__).parent / ".." / "source" / "_inserts"

if __name__ == "__main__":
    DPATH_INSERTS.mkdir(parents=True, exist_ok=True)
    nipoppy.utils.fileops.copy_template(
        FPATH_SAMPLE_CONFIG,
        DPATH_INSERTS / "sample_study_config.json",
        version=PROGRAM_VERSION,
    )
