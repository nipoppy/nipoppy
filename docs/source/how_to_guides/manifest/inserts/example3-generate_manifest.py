#!/usr/bin/env python
"""Manifest-generation script for Example 3."""

from pathlib import Path

import pandas as pd

if __name__ == "__main__":

    # get the path to the data directory
    # we assume that it is in the same directory as this script
    path_data = Path(__file__).parent / "data"

    data_for_manifest = []
    for path_participant in sorted(path_data.iterdir()):
        for path_participant_visit in sorted(path_participant.iterdir()):
            participant_id = path_participant.name
            visit_id = path_participant_visit.name
            session_id = visit_id
            datatype = []

            if (path_participant_visit / "T1w").exists():
                datatype.append("anat")
            if (path_participant_visit / "diffusion").exists():
                datatype.append("dwi")

            # create the manifest entry
            data_for_manifest.append(
                {
                    "participant_id": participant_id,
                    "visit_id": visit_id,
                    "session_id": session_id,
                    "datatype": datatype,
                }
            )

    df_manifest = pd.DataFrame(data_for_manifest)

    # write the manifest in the same directory as this script
    df_manifest.to_csv(
        Path(__file__).parent / "example3-manifest.tsv", sep="\t", index=False
    )
