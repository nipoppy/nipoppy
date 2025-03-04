#!/usr/bin/env python
"""An example script to generate a manifest file from a demographics file."""

from pathlib import Path

import pandas as pd

if __name__ == "__main__":

    # get the path to the demographics file
    # we assume that it is in the same directory as this script
    path_demographics = Path(__file__).parent / "example2-demographics.csv"

    # load the demographics file
    df_demographics = pd.read_csv(path_demographics, dtype=str)

    # all participants only have anat datatype
    datatype = ["anat"]

    data_for_manifest = []
    for _, row in df_demographics.iterrows():

        # remove underscores
        participant_id = row["PARTICIPANT"].replace("_", "")

        # each row in the demographics file is multiple rows in the manifest file
        for visit_id in [
            "NEUROPSYCH_1",
            "NEUROPSYCH_2",
            "NEUROPSYCH_3",
            "MRI_1",
            "MRI_2",
        ]:

            # if the AGE column is empty, the visit did not happen yet
            if pd.isna(row[f"AGE_{visit_id}"]):
                continue

            # session_id is only defined for MRI visits
            if visit_id.startswith("MRI_"):
                session_id = visit_id.removeprefix("MRI_")
            else:
                session_id = pd.NA

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
        Path(__file__).parent / "example2-manifest.tsv", sep="\t", index=False
    )
