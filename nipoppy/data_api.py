"""Nipoppy data API."""

from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from nipoppy.env import StrOrPathLike
from nipoppy.study import Study
from nipoppy.tabular.manifest import Manifest
from nipoppy.utils.bids import check_participant_id, check_session_id

# Neurobagel TermURLs for identifier columns
TERMURL_PARTICIPANT_ID = "nb:ParticipantID"
TERMURL_SESSION_ID = "nb:SessionID"


def _check_phenotypes_arg(phenotypes: List[str]) -> None:
    if not isinstance(phenotypes, List):
        raise TypeError(f"phenotypes must be a list, got {type(phenotypes)}")
    if len(phenotypes) == 0:
        raise ValueError("phenotypes list cannot be empty")
    for term_url in phenotypes:
        if not isinstance(term_url, str):
            raise TypeError(
                f"Phenotype must be a string, got {type(term_url)} for {term_url}"
            )


def _check_derivatives_arg(derivatives: List[Tuple[str, str, str]]) -> None:
    if not isinstance(derivatives, List):
        raise TypeError(
            f"derivatives must be a list of tuples, got {type(derivatives)}"
        )
    if len(derivatives) == 0:
        raise ValueError("derivatives list cannot be empty")
    for derivatives_spec in derivatives:
        if not (
            isinstance(derivatives_spec, Tuple)
            and len(derivatives_spec) == 3
            and all(isinstance(item, str) for item in derivatives_spec)
        ):
            raise TypeError(
                "Each derivative specification must be a tuple containing 3 strings"
                " (pipeline_name, pipeline_version, filepath_pattern)"
                f", got invalid specification {derivatives_spec}"
            )


class NipoppyDataAPI:
    """API for getting data from a Nipoppy study."""

    index_cols_derivatives = [Manifest.col_participant_id, Manifest.col_session_id]
    index_cols_phenotypes = [TERMURL_PARTICIPANT_ID, TERMURL_SESSION_ID]
    index_cols_output = [Manifest.col_participant_id, Manifest.col_session_id]

    def __init__(self, study: Study):
        """Instantiate a NipoppyDataAPI object.

        Parameters
        ----------
        study : Study
            The Nipoppy study object.
        """
        self.study = study

    def _load_tsv(self, fpath: StrOrPathLike, index_cols: List[str]) -> pd.DataFrame:
        df = pd.read_csv(
            fpath,
            sep="\t",
            index_col=index_cols,
            dtype={col: str for col in index_cols},
        )

        # strip BIDS prefixes if they are present
        df.index = df.index.map(
            lambda idx: (check_participant_id(idx[0]), check_session_id(idx[1]))
        )

        # rename index columns
        df.index.names = self.index_cols_output

        return df

    def _find_derivatives_path(
        self,
        pipeline_name: str,
        pipeline_version: str,
        filepath_pattern: str,
    ) -> Path:
        candidate_paths_list = list(
            self.study.layout.get_dpath_pipeline(
                pipeline_name=pipeline_name, pipeline_version=pipeline_version
            ).glob(filepath_pattern)
        )
        if len(candidate_paths_list) == 0:
            raise FileNotFoundError(
                f"No file matching {filepath_pattern} for pipeline "
                f"{pipeline_name}, version {pipeline_version}"
            )
        elif len(candidate_paths_list) > 1:
            raise ValueError(
                f"Found more than one file matching {filepath_pattern} for pipeline "
                f"{pipeline_name}, version {pipeline_version}: {candidate_paths_list}"
            )
        return candidate_paths_list.pop()

    def _get_derivatives_table(
        self,
        pipeline_name: str,
        pipeline_version: str,
        filepath_pattern: str,
    ) -> pd.DataFrame:
        return self._load_tsv(
            self._find_derivatives_path(
                pipeline_name, pipeline_version, filepath_pattern
            ),
            index_cols=self.index_cols_derivatives,
        )

    def _filter_with_manifest(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.loc[df.index.isin(self.study.manifest.get_participants_sessions()), :]

    def get_phenotypes(self, phenotypes: List[str]) -> pd.DataFrame:
        """Get harmonized phenotypic data from the Nipoppy study.

        This function loads the study's harmonized phenotypic TSV file
        (`<NIPOPPY_ROOT>/tabular/harmonized.tsv`). It then subsets the data to include
        only the requested phenotypic columns, and filters the rows to include only
        participants and sessions that are present in the study's manifest.

        The harmonized phenotypic TSV file is expected to have columns
        "nb:ParticipantID" and "nb:SessionID" for participant and session identifiers.

        Parameters
        ----------
        phenotypes : List[str]
            List of Neurobagel TermURLs corresponding to phenotypic (demographics,
            assessments, etc.) columns to retrieve.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the requested phenotypic data, with a MultiIndex of
            participant IDs and session IDs.
        """
        _check_phenotypes_arg(phenotypes)
        df = self._load_tsv(
            self.study.layout.fpath_harmonized, index_cols=self.index_cols_phenotypes
        )
        df = self._filter_with_manifest(df)
        return df.loc[:, phenotypes]

    def get_derivatives(self, derivatives: List[Tuple[str, str, str]]) -> pd.DataFrame:
        """Get derivative data from the Nipoppy study.

        This functions loads and combines derivative TSV files from specified pipelines
        and versions, based on the provided filepath patterns. It filters the rows to
        include only participants and sessions that are present in the study's manifest.

        The derivatives TSV files are expected to have columns "participant_id" and
        "session_id" for participant and session identifiers.

        Parameters
        ----------
        derivatives : List[Tuple[str, str, str]]
            List of (`pipeline_name`, `pipeline_version`, `filepath_pattern`) tuples,
            for specifying derivative data to retrieve. `filepath_patterrn` may include
            wildcards as per `pathlib.Path.glob()`.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the requested derivative data, with a MultiIndex of
            participant IDs and session IDs.
        """
        _check_derivatives_arg(derivatives)
        dfs = []
        for pipeline_name, pipeline_version, filepath_pattern in derivatives:
            dfs.append(
                self._get_derivatives_table(
                    pipeline_name, pipeline_version, filepath_pattern
                )
            )
        df = pd.concat(dfs, axis="columns", join="outer")
        df = self._filter_with_manifest(df)
        return df

    def get_tabular_data(
        self,
        phenotypes: Optional[List[str]] = None,
        derivatives: Optional[List[Tuple[str, str, str]]] = None,
    ) -> pd.DataFrame:
        """Get harmonized tabular data from the Nipoppy study.

        This is a high-level wrapper function that combines phenotypic and derivative
        data retrieval.

        Harmonized phenotypic data is loaded from the TSV file at
        `<NIPOPPY_ROOT>/tabular/harmonized.tsv` and subsetted to include only the
        requested phenotypic column. This file is expected to have columns
        "nb:ParticipantID" and "nb:SessionID" for participant and session identifiers.

        Derivative data is loaded from the specified pipelines and versions, based on
        the provided filepath patterns. These TSV files are expected to have columns
        "participant_id" and "session_id" for participant and session identifiers.

        "nb:ParticipantID" and "participant_id" columns are assumed to correspond to
        each other, as are "nb:SessionID" and "session_id".

        The output dataframe will only contain participants and sessions that are
        present in the study's manifest.

        Parameters
        ----------
        phenotypes : Optional[List[str]]
            List of Neurobagel TermURLs, for specifying phenotypic (demographics,
            assessments, etc.) data to retrieve.
        derivatives : Optional[List[Tuple[str, str, str]]]
            List of (`pipeline_name`, `pipeline_version`, `filepath_pattern`) tuples,
            for specifying derivative data to retrieve. `filepath_patterrn` may include
            wildcards as per `pathlib.Path.glob()`.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the requested phenotypic and derivative data, with
            a MultiIndex of participant IDs and session IDs.
        """
        if not (phenotypes or derivatives):
            raise ValueError("Must request at least one measure")

        dfs = []
        if phenotypes:
            dfs.append(self.get_phenotypes(phenotypes))
        if derivatives:
            dfs.append(self.get_derivatives(derivatives))
        return pd.concat(dfs, axis="columns", join="outer")
