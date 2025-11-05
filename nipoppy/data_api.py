"""Nipoppy data API."""

from functools import cached_property
from typing import List, Optional, Tuple

import pandas as pd

from nipoppy.env import StrOrPathLike
from nipoppy.study import Study
from nipoppy.tabular.manifest import Manifest


class NipoppyDataAPI:
    """API for getting data from a Nipoppy study."""

    imaging_index_cols = [Manifest.col_participant_id, Manifest.col_session_id]

    def __init__(self, dpath_root: StrOrPathLike):
        """Instantiate a NipoppyDataAPI object.

        Currently, only the default dataset layout is supported.

        Parameters
        ----------
        dpath_root : StrOrPathLike
            Path to the root directory.
        """
        self.dpath_root = dpath_root

    @cached_property
    def study(self) -> Study:
        """The Nipoppy study object for the dataset."""
        return Study(dpath_root=self.dpath_root)

    def _load_tsv(self, fpath: StrOrPathLike, index_cols: List[str]) -> pd.DataFrame:
        return pd.read_csv(
            fpath,
            sep="\t",
            index_col=index_cols,
            dtype={col: str for col in index_cols},
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

    def _get_derivatives_table(
        self,
        pipeline_name: str,
        pipeline_version: str,
        filepath_pattern: str,
    ) -> pd.DataFrame:
        candidate_paths = list(
            self.study.layout.get_dpath_pipeline(
                pipeline_name=pipeline_name, pipeline_version=pipeline_version
            ).glob(filepath_pattern)
        )
        if len(candidate_paths) == 0:
            raise FileNotFoundError(
                f"No file matching {filepath_pattern} for pipeline "
                f"{pipeline_name}, version {pipeline_version}"
            )
        elif len(candidate_paths) > 1:
            raise RuntimeError(
                f"Found more than one file matching {filepath_pattern} for pipeline "
                f"{pipeline_name}, version {pipeline_version}: {candidate_paths}"
            )
        return self._load_tsv(candidate_paths.pop(), index_cols=self.imaging_index_cols)

    def get_tabular_data(
        self,
        derivatives: Optional[List[Tuple[str, str, str]]] = None,
    ) -> pd.DataFrame:
        """Get tabular data from the Nipoppy dataset.

        Parameters
        ----------
        derivatives : Optional[List[Tuple[str, str, str]]]
            List of (pipeline_name, pipeline_version, filepath_pattern) tuples, for
            specifying derivative data to retrieve

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the requested demographic and derivative data, with
            a MultiIndex of participant IDs and session IDs.
        """
        # input validation
        if derivatives is None:
            derivatives = []
        # NOTE this will make more sense once demographic data is supported
        if not derivatives:
            raise ValueError(
                "At least one derivative/demographic specification must be defined."
            )

        dfs = []
        for derivatives_spec in derivatives:
            dfs.append(self._get_derivatives_table(*derivatives_spec))

        df = pd.concat(dfs, axis="columns", join="outer")

        # only use participants/sessions from the manifest
        df = df.loc[df.index.isin(self.study.manifest.get_participants_sessions()), :]

        return df
