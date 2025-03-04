#!/usr/bin/env python
"""An example script to generate a manifest file from another tabular file."""

from pathlib import Path

import pandas as pd

if __name__ == "__main__":

    # get the path to the participants file
    # we assume that it is in the same directory as this script
    path_participants = Path(__file__).parent / "example1-participants.csv"

    # load the participants file
    # note that the participant column is read as a string because
    # otherwise the leading zeros would be removed
    df_participants = pd.read_csv(path_participants, dtype={"participant": str})

    data_for_manifest = []
    for _, row in df_participants.iterrows():

        # no change for participant_id
        participant_id = row["participant"]

        # use the same visit_id and session_id for all participants
        # since the study is cross-sectional
        visit_id = 1
        session_id = 1

        # all participants have anat data
        datatype = ["anat"]
        if row["dwi"]:
            datatype.append("dwi")
        if row["func"]:
            datatype.append("func")

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
        Path(__file__).parent / "example1-manifest.tsv", sep="\t", index=False
    )
