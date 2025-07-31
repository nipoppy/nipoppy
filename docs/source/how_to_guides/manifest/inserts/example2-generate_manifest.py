#!/usr/bin/env python
"""Manifest-generation script for Example 2."""

from pathlib import Path

import pandas as pd

if __name__ == "__main__":

    # get the path to the demographics/neuropsych file and the MRI file
    # we assume that it is in the same directory as this script
    path_neuropsych = Path(__file__).parent / "example2-demographics_neuropsych.csv"
    path_mri = Path(__file__).parent / "example2-mri.csv"

    # load the files and merge them
    df_neuropsych = pd.read_csv(path_neuropsych, dtype=str)
    df_mri = pd.read_csv(path_mri, dtype=str)
    df_merged = pd.merge(
        df_neuropsych, df_mri, how="left", left_on="PARTICIPANT", right_on="PARTICIPANT"
    )

    data_for_manifest = []
    for _, row in df_merged.iterrows():

        # remove underscores
        participant_id = row["PARTICIPANT"].replace("_", "")

        # each row in the demographics file is multiple rows in the manifest file
        for visit_id in [
            "NEUROPSYCH1",
            "NEUROPSYCH2",
            "NEUROPSYCH3",
            "MRI1",
            "MRI2",
        ]:

            # if the DATE column is empty, the visit did not happen yet
            if pd.isna(row[f"DATE_{visit_id}"]):
                continue

            # session_id is only defined for MRI visits
            if visit_id.startswith("MRI"):
                session_id = visit_id.removeprefix("MRI")

                # all participants only have anat datatype
                datatype = ["anat"]
            else:
                session_id = pd.NA
                datatype = []

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
