"""Nipoppy data API."""

from typing import List, Optional, Tuple

import pandas as pd

from nipoppy.env import StrOrPathLike
from nipoppy.study import Study
from nipoppy.tabular.manifest import Manifest
from nipoppy.utils.bids import check_participant_id, check_session_id

# Neurobagel TermURLs for identifier columns
TERMURL_PARTICIPANT_ID = "nb:ParticipantID"
TERMURL_SESSION_ID = "nb:SessionID"


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

    def _check_phenotypes_arg(
        self,
        phenotypes: List[str],
    ) -> None:
        if not isinstance(phenotypes, List):
            raise TypeError(f"phenotypes must be a list, got {type(phenotypes)}")
        for term_url in phenotypes:
            if not isinstance(term_url, str):
                raise TypeError(
                    f"Phenotype must be a string, got {type(term_url)} for {term_url}"
                )

    def _check_derivatives_arg(
        self,
        derivatives: List[Tuple[str, str, str]],
    ) -> None:
        if not isinstance(derivatives, List):
            raise TypeError(
                f"derivatives must be a list of tuples, got {type(derivatives)}"
            )
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

    def _get_phenotypes_table(self, phenotypes: List[str]) -> pd.DataFrame:
        return self._load_tsv(
            self.study.layout.fpath_harmonized, index_cols=self.index_cols_phenotypes
        ).loc[:, phenotypes]

    def _get_derivatives_table(
        self,
        pipeline_name: str,
        pipeline_version: str,
        filepath_pattern: str,
    ) -> pd.DataFrame:
        candidate_path = list(
            self.study.layout.get_dpath_pipeline(
                pipeline_name=pipeline_name, pipeline_version=pipeline_version
            ).rglob(filepath_pattern)
        )
        if len(candidate_path) == 0:
            raise FileNotFoundError(
                f"No file matching {filepath_pattern} for pipeline "
                f"{pipeline_name}, version {pipeline_version}"
            )
        elif len(candidate_path) > 1:
            raise RuntimeError(
                f"Found more than one file matching {filepath_pattern} for pipeline "
                f"{pipeline_name}, version {pipeline_version}: {candidate_path}"
            )
        return self._load_tsv(
            candidate_path.pop(), index_cols=self.index_cols_derivatives
        )

    def get_tabular_data(
        self,
        phenotypes: Optional[List[str]] = None,
        derivatives: Optional[List[Tuple[str, str, str]]] = None,
    ) -> pd.DataFrame:
        """Get harmonized tabular data from the Nipoppy dataset.

        Parameters
        ----------
        phenotypes : Optional[List[str]]
            List of Neurobagel TermURLs, for specifying phenotypic (demographics,
            assessments, etc.) data to retrieve
        derivatives : Optional[List[Tuple[str, str, str]]]
            List of (pipeline_name, pipeline_version, filepath_pattern) tuples, for
            specifying derivative data to retrieve

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the requested phenotypic and derivative data, with
            a MultiIndex of participant IDs and session IDs.
        """
        if phenotypes is None:
            phenotypes = []
        if derivatives is None:
            derivatives = []
        if not (phenotypes or derivatives):
            raise ValueError("Must request at least one measure")
        self._check_phenotypes_arg(phenotypes)
        self._check_derivatives_arg(derivatives)

        dfs = []
        if phenotypes:
            dfs.append(self._get_phenotypes_table(phenotypes))
        for pipeline_name, pipeline_version, filepath_pattern in derivatives:
            dfs.append(
                self._get_derivatives_table(
                    pipeline_name, pipeline_version, filepath_pattern
                )
            )

        df = pd.concat(dfs, axis="columns", join="outer")

        # only use participants/sessions from the manifest
        df = df.loc[df.index.isin(self.study.manifest.get_participants_sessions()), :]

        return df
