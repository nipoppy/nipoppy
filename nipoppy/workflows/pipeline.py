"""Base class for pipeline workflows."""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, List, Optional, Tuple, Type

import pandas as pd
from packaging.version import Version

from nipoppy.config.boutiques import BoutiquesConfig
from nipoppy.config.hpc import HpcConfig
from nipoppy.config.pipeline import (
    BasePipelineConfig,
    BIDSificationPipelineConfig,
    ExtractionPipelineConfig,
    ProcessingPipelineConfig,
)
from nipoppy.config.pipeline_step import AnalysisLevelType, ProcPipelineStepConfig
from nipoppy.config.tracker import TrackerConfig
from nipoppy.container import get_container_handler
from nipoppy.env import (
    BIDS_SESSION_PREFIX,
    BIDS_SUBJECT_PREFIX,
    FAKE_SESSION_ID,
    LogColor,
    PipelineTypeEnum,
    ReturnCode,
    StrOrPathLike,
)
from nipoppy.layout import DatasetLayout
from nipoppy.utils.bids import (
    add_pybids_ignore_patterns,
    check_participant_id,
    check_session_id,
    create_bids_db,
)
from nipoppy.utils.utils import get_pipeline_tag, load_json
from nipoppy.workflows.base import BaseDatasetWorkflow
from nipoppy.workflows.pipeline_config_loader import PipelineConfigLoader
from nipoppy.workflows.pipeline_executor import JOBLIB_INSTALLED, PipelineExecutor
from nipoppy.workflows.pipeline_hpc import PipelineHpcSubmitter

# Re-export for backward compatibility with tests and external code
try:
    from joblib import Parallel, delayed
except ImportError:
    delayed = None
    Parallel = None

import rich
import rich.progress

if TYPE_CHECKING:
    import bids


def apply_analysis_level(
    participants_sessions: Iterable[str, str],
    analysis_level: AnalysisLevelType,
) -> List[Tuple[str, str]]:
    """Filter participant-session pairs to run based on the analysis level."""
    if analysis_level == AnalysisLevelType.group:
        return [(None, None)]

    elif analysis_level == AnalysisLevelType.participant:
        participants = []
        for participant, _ in participants_sessions:
            if participant not in participants:
                participants.append(participant)
        return [(participant, None) for participant in participants]

    elif analysis_level == AnalysisLevelType.session:
        sessions = []
        for _, session in participants_sessions:
            if session not in sessions:
                sessions.append(session)
        return [(None, session) for session in sessions]

    else:
        return list(participants_sessions)


def get_pipeline_version(
    pipeline_name: str,
    dpath_pipelines: StrOrPathLike,
) -> str:
    """Get the latest version associated with a pipeline.

    Parameters
    ----------
    pipeline_name : str
        Name of the pipeline, as specified in the config
    dpath_pipelines : nipoppy.env.StrOrPathLike
        Path to directory containing pipeline bundle subdirectories

    Returns
    -------
    str
        The pipeline version
    """
    installed_pipelines = []
    pipeline_config_latest = None
    for fpath_pipeline_config in Path(dpath_pipelines).glob(
        f"*/{DatasetLayout.fname_pipeline_config}"
    ):
        pipeline_config = BasePipelineConfig(**load_json(fpath_pipeline_config))
        if pipeline_config.NAME == pipeline_name:
            if pipeline_config_latest is None:
                pipeline_config_latest = pipeline_config
            elif Version(pipeline_config.VERSION) > Version(
                pipeline_config_latest.VERSION
            ):
                pipeline_config_latest = pipeline_config
        installed_pipelines.append((pipeline_config.NAME, pipeline_config.VERSION))

    if pipeline_config_latest is not None:
        return pipeline_config_latest.VERSION
    else:
        raise ValueError(
            f"No config found for pipeline with NAME={pipeline_name}"
            ". Installed pipelines: "
            + ", ".join(f"{name} {version}" for name, version in installed_pipelines)
        )


class BasePipelineWorkflow(BaseDatasetWorkflow, ABC):
    """A workflow for a pipeline that has a Boutiques descriptor."""

    # Legacy attributes kept for backward compatibility
    dname_hpc_logs = "hpc"
    fname_hpc_error = "pysqa.err"
    fname_job_script = "run_queue.sh"

    _pipeline_type = PipelineTypeEnum.PROCESSING

    _pipeline_type_to_pipeline_class_map = {
        PipelineTypeEnum.PROCESSING: ProcessingPipelineConfig,
        PipelineTypeEnum.BIDSIFICATION: BIDSificationPipelineConfig,
        PipelineTypeEnum.EXTRACTION: ExtractionPipelineConfig,
    }

    progress_bar_description = "Working..."  # default description used by rich

    def __init__(
        self,
        dpath_root: StrOrPathLike,
        name: str,
        pipeline_name: str,
        pipeline_version: Optional[str] = None,
        pipeline_step: Optional[str] = None,
        participant_id: str = None,
        session_id: str = None,
        use_subcohort: Optional[StrOrPathLike] = None,
        hpc: Optional[str] = None,
        write_subcohort: Optional[StrOrPathLike] = None,
        n_jobs: Optional[int] = None,
        fpath_layout: Optional[StrOrPathLike] = None,
        verbose: bool = False,
        dry_run=False,
        _skip_logfile: bool = False,
        _show_progress: bool = False,
    ):
        if hpc and write_subcohort:
            raise ValueError(
                "HPC job submission and writing a list of participants and sessions "
                "are mutually exclusive."
            )

        if n_jobs is not None and not _skip_logfile:
            raise ValueError("n_jobs is not supported when _skip_logfile is False.")
        if n_jobs is None:
            n_jobs = 1

        self.pipeline_name = pipeline_name
        self.pipeline_version = pipeline_version
        self.pipeline_step = pipeline_step
        self.participant_id = check_participant_id(participant_id)
        self.session_id = check_session_id(session_id)
        self.use_subcohort = use_subcohort
        self.hpc = hpc
        self.write_subcohort = write_subcohort
        self.n_jobs = n_jobs
        self._show_progress = _show_progress

        super().__init__(
            dpath_root=dpath_root,
            name=name,
            fpath_layout=fpath_layout,
            verbose=verbose,
            dry_run=dry_run,
            _skip_logfile=_skip_logfile,
        )

        # the message logged in run_cleanup will depend on
        # the final values for these attributes (updated in run_main)
        self.n_success = 0
        self.n_total = 0

        self.run_single_results = None

        if not JOBLIB_INSTALLED and self.n_jobs not in (None, 1):
            self.logger.error(
                "An additional dependency is required to enable local parallelization "
                "with --n-jobs. Install it with: pip install nipoppy[parallel]",
                extra={"markup": False},
            )
            sys.exit(ReturnCode.MISSING_DEPENDENCY)

        # Initialize helper objects (lazy initialization via properties)
        self._config_loader = None
        self._executor = None
        self._hpc_submitter = None

    @property
    def config_loader(self) -> PipelineConfigLoader:
        """Get the configuration loader instance."""
        if self._config_loader is None:
            self._config_loader = PipelineConfigLoader(
                layout=self.layout,
                logger=self.logger,
                config=self.config,
                dpath_pipeline_bundle=self.dpath_pipeline_bundle,
                # Pass a lambda that calls the workflow's process_template_json
                # This ensures the workflow's method is called (for test mocking)
                process_template_json_callback=lambda **kwargs: self._process_template_json_impl(**kwargs),
            )
        return self._config_loader
    
    def _process_template_json_impl(self, template_json, participant_id=None, session_id=None, 
                                     bids_participant_id=None, bids_session_id=None, 
                                     objs=None, return_str=False, with_substitutions=True, **kwargs):
        """Internal implementation of process_template_json."""
        # This is the actual implementation that was in process_template_json
        # It's called by the callback
        if objs is None:
            objs = []
        if self not in objs:
            objs.insert(0, self)
        
        # Call the config_loader's process_template_json implementation directly
        # but disable the callback to avoid recursion
        saved_callback = self._config_loader._process_template_json_callback
        self._config_loader._process_template_json_callback = None
        try:
            return self._config_loader.process_template_json(
                template_json=template_json,
                participant_id=participant_id,
                session_id=session_id,
                bids_participant_id=bids_participant_id,
                bids_session_id=bids_session_id,
                objs=objs,
                return_str=return_str,
                with_substitutions=with_substitutions,
                **kwargs,
            )
        finally:
            self._config_loader._process_template_json_callback = saved_callback

    @property
    def executor(self) -> PipelineExecutor:
        """Get the pipeline executor instance."""
        if self._executor is None:
            self._executor = PipelineExecutor(
                logger=self.logger,
                pipeline_name=self.pipeline_name,
                pipeline_version=self.pipeline_version,
                n_jobs=self.n_jobs,
                show_progress=self._show_progress,
                progress_bar_description=self.progress_bar_description,
            )
        return self._executor

    @property
    def hpc_submitter(self) -> PipelineHpcSubmitter:
        """Get the HPC submitter instance."""
        if self._hpc_submitter is None:
            self._hpc_submitter = PipelineHpcSubmitter(
                layout=self.layout,
                logger=self.logger,
                hpc_config=self.hpc_config,
                hpc_preamble=self.config.HPC_PREAMBLE,
                dry_run=self.dry_run,
            )
        return self._hpc_submitter

    @cached_property
    def dpaths_to_check(self) -> list[Path]:
        """Directory paths to create if needed during the setup phase."""
        return []

    @cached_property
    def dpath_pipeline(self) -> Path:
        """Return the path to the pipeline's derivatives directory."""
        return self.layout.get_dpath_pipeline(
            pipeline_name=self.pipeline_name, pipeline_version=self.pipeline_version
        )

    @cached_property
    def dpath_pipeline_output(self) -> Path:
        """Return the path to the pipeline's output directory."""
        return self.layout.get_dpath_pipeline_output(
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version,
        )

    @cached_property
    def dpath_pipeline_work(self) -> Path:
        """Return the path to the pipeline's working directory."""
        return self.layout.get_dpath_pipeline_work(
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version,
            participant_id=self.participant_id,
            session_id=self.session_id,
        )

    @cached_property
    def dpath_pipeline_bids_db(self) -> Path:
        """Return the path to the pipeline's BIDS database directory."""
        return self.layout.get_dpath_pybids_db(
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version,
            participant_id=self.participant_id,
            session_id=self.session_id,
        )

    @cached_property
    def dpath_pipeline_bundle(self) -> Path:
        """Path to the pipeline bundle directory."""
        return self.layout.get_dpath_pipeline_bundle(
            self._pipeline_type,
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version,
        )

    @cached_property
    def pipeline_config(self) -> ProcessingPipelineConfig:
        """Get the user config object for the processing pipeline."""
        return self.config_loader.load_pipeline_config(
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version,
            pipeline_type=self._pipeline_type,
            pipeline_class=self._pipeline_type_to_pipeline_class_map[
                self._pipeline_type
            ],
        )

    @cached_property
    def pipeline_step_config(self) -> ProcPipelineStepConfig:
        """Get the user config for the pipeline step."""
        return self.pipeline_config.get_step_config(step_name=self.pipeline_step)

    @cached_property
    def fpath_container(self) -> Path:
        """Return the full path to the pipeline's container."""
        uri = self.pipeline_config.CONTAINER_INFO.URI
        fpath_container = self.pipeline_config.CONTAINER_INFO.FILE
        container_handler = get_container_handler(
            self.pipeline_step_config.CONTAINER_CONFIG,
            logger=self.logger,
        )

        try:
            is_downloaded = container_handler.is_image_downloaded(uri, fpath_container)
        except ValueError as exception:
            raise ValueError(
                f"Error in container config for pipeline {self.pipeline_name} "
                f"{self.pipeline_version}: {exception}"
            )

        if not is_downloaded:
            error_message = (
                f"No container image file found for pipeline"
                f" {self.pipeline_name} {self.pipeline_version}"
            )
            if uri is not None:
                pull_command = container_handler.get_pull_command(uri, fpath_container)
                error_message += (
                    ". This file can be downloaded to the appropriate path by running "
                    f"the following command:\n\n{pull_command}"
                )
            raise FileNotFoundError(error_message)

        return fpath_container

    @cached_property
    def descriptor(self) -> dict:
        """Load the pipeline step's Boutiques descriptor."""
        return self.config_loader.load_descriptor(
            fname_descriptor=self.pipeline_step_config.DESCRIPTOR_FILE,
            pipeline_type=self.pipeline_config.PIPELINE_TYPE,
            pipeline_name=self.pipeline_config.NAME,
            pipeline_version=self.pipeline_config.VERSION,
        )

    @cached_property
    def invocation(self) -> dict:
        """Load the pipeline step's Boutiques invocation."""
        return self.config_loader.load_invocation(
            fname_invocation=self.pipeline_step_config.INVOCATION_FILE,
            pipeline_type=self.pipeline_config.PIPELINE_TYPE,
            pipeline_name=self.pipeline_config.NAME,
            pipeline_version=self.pipeline_config.VERSION,
        )

    @cached_property
    def tracker_config(self) -> TrackerConfig:
        """Load the pipeline step's tracker configuration."""
        return self.config_loader.load_tracker_config(
            fname_tracker_config=self.pipeline_step_config.TRACKER_CONFIG_FILE,
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version,
        )

    @cached_property
    def pybids_ignore_patterns(self) -> list[str]:
        """
        Load the pipeline step's PyBIDS ignore pattern list.

        Note: this does not apply any substitutions, since the subject/session
        patterns are always added.
        """
        return self.config_loader.load_pybids_ignore_patterns(
            fname_pybids_ignore=self.pipeline_step_config.PYBIDS_IGNORE_FILE
        )

    @cached_property
    def hpc_config(self) -> HpcConfig:
        """Load the pipeline step's HPC configuration."""
        return self.config_loader.load_hpc_config(
            fname_hpc_config=self.pipeline_step_config.HPC_CONFIG_FILE
        )

    @cached_property
    def boutiques_config(self):
        """Get the Boutiques configuration."""
        return self.config_loader.load_boutiques_config(self.descriptor)

    def _get_pipeline_config(
        self,
        dpath_pipeline_bundle: Path,
        pipeline_name: str,
        pipeline_version: str,
        pipeline_class: Type[BasePipelineConfig],
    ) -> BasePipelineConfig:
        """Get the config for a pipeline.
        
        This method is maintained for backward compatibility.
        It delegates to the config_loader's load_pipeline_config.
        """
        # Create a temporary config_loader if needed
        temp_config_loader = PipelineConfigLoader(
            layout=self.layout,
            logger=self.logger,
            config=self.config,
            dpath_pipeline_bundle=dpath_pipeline_bundle,
        )
        return temp_config_loader.load_pipeline_config(
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            pipeline_type=self._pipeline_type,
            pipeline_class=pipeline_class,
        )

    def process_template_json(
        self,
        template_json: dict,
        participant_id: Optional[str] = None,
        session_id: Optional[str] = None,
        bids_participant_id: Optional[str] = None,
        bids_session_id: Optional[str] = None,
        objs: Optional[list] = None,
        return_str: bool = False,
        with_substitutions: bool = True,
        **kwargs,
    ):
        """Replace template strings in a JSON object.
        
        This is the main public API for template processing.
        """
        return self._process_template_json_impl(
            template_json=template_json,
            participant_id=participant_id,
            session_id=session_id,
            bids_participant_id=bids_participant_id,
            bids_session_id=bids_session_id,
            objs=objs,
            return_str=return_str,
            with_substitutions=with_substitutions,
            **kwargs,
        )

    def set_up_bids_db(
        self,
        dpath_pybids_db: StrOrPathLike,
        participant_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> bids.BIDSLayout:
        """Set up the BIDS database."""
        dpath_pybids_db: Path = Path(dpath_pybids_db)

        pybids_ignore_patterns = self.pybids_ignore_patterns.copy()

        if participant_id is not None:
            add_pybids_ignore_patterns(
                current=pybids_ignore_patterns,
                new=f"^(?!/{BIDS_SUBJECT_PREFIX}({participant_id}))",
            )
        if (session_id is not None) and (session_id != FAKE_SESSION_ID):
            add_pybids_ignore_patterns(
                current=pybids_ignore_patterns,
                new=f".*?/{BIDS_SESSION_PREFIX}(?!{session_id})",
            )

        self.logger.info(
            f"Building BIDSLayout with {len(pybids_ignore_patterns)} ignore "
            f"patterns: {pybids_ignore_patterns}"
        )

        if dpath_pybids_db.exists() and list(dpath_pybids_db.iterdir()):
            self.logger.warning(
                f"Overwriting existing BIDS database directory: {dpath_pybids_db}"
            )

        self.logger.debug(f"Path to BIDS data: {self.layout.dpath_bids}")
        bids_layout: bids.BIDSLayout = create_bids_db(
            dpath_bids=self.layout.dpath_bids,
            dpath_pybids_db=dpath_pybids_db,
            ignore_patterns=pybids_ignore_patterns,
            reset_database=True,
        )

        # list all the files in BIDSLayout
        # since we are selecting for specific a specific subject and
        # session, there should not be too many files
        filenames = bids_layout.get(return_type="filename")
        self.logger.debug(f"Found {len(filenames)} files in BIDS database:")
        for filename in filenames:
            self.logger.debug(filename)

        if len(filenames) == 0:
            self.logger.warning("BIDS database is empty")

        return bids_layout

    def check_dir(self, dpath: Path):
        """Create directory if it does not exist."""
        if not dpath.exists():
            self.mkdir(dpath)

    def check_pipeline_version(self):
        """Set the pipeline version based on the config if it is not given."""
        if self.pipeline_version is None:
            self.pipeline_version = get_pipeline_version(
                pipeline_name=self.pipeline_name,
                dpath_pipelines=self.layout.get_dpath_pipeline_store(
                    self._pipeline_type
                ),
            )
            self.logger.warning(
                f"Pipeline version not specified, using version {self.pipeline_version}"
            )

    def _check_pipeline_variables(self):
        """Check that the pipeline variables are not null in the config."""
        for name, value in self.config.PIPELINE_VARIABLES.get_variables(
            self._pipeline_type, self.pipeline_name, self.pipeline_version
        ).items():
            if value is None:
                raise ValueError(
                    f"Variable {name} is not set in the config for pipeline "
                    f"{self.pipeline_name}, version {self.pipeline_version}. You need "
                    "to set it in the PIPELINE_VARIABLES section of the config file at "
                    f"{self.layout.fpath_config}"
                )

    def check_pipeline_step(self):
        """Set the pipeline step name based on the config if it is not given."""
        if self.pipeline_step is None:
            self.pipeline_step = self.pipeline_step_config.NAME
            self.logger.warning(
                f"Pipeline step not specified, using step {self.pipeline_step}"
            )

    def run_setup(self):
        """Run pipeline setup."""
        to_return = super().run_setup()

        self.check_pipeline_version()
        self._check_pipeline_variables()
        self.check_pipeline_step()

        for dpath in self.dpaths_to_check:
            self.check_dir(dpath)

        return to_return

    def _run_single_wrapper(self, participant_id, session_id) -> bool:
        """
        Run a single participant/session and handle exceptions.

        This method is maintained for backward compatibility.
        It delegates to the executor's run_single_wrapper.
        """
        return self.executor.run_single_wrapper(
            self.run_single, participant_id, session_id
        )

    def _get_results_generator(self, participants_sessions: Iterable[Tuple[str, str]]):
        """
        Get a generator for execution results.

        This method is maintained for backward compatibility.
        It delegates to the executor's get_results_generator.
        """
        return self.executor.get_results_generator(
            self.run_single, participants_sessions
        )

    def run_main(self):
        """Run the pipeline."""
        participants_sessions = self.get_participants_sessions_to_run(
            self.participant_id, self.session_id
        )

        if self.use_subcohort is not None:
            try:
                df_participants_sessions = pd.read_csv(
                    self.use_subcohort, header=None, sep="\t", dtype=str
                )
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"Subcohort file {self.use_subcohort} not found"
                )
            except pd.errors.EmptyDataError:
                raise RuntimeError(f"Subcohort file {self.use_subcohort} is empty")

            participants_sessions = set(participants_sessions) & set(
                df_participants_sessions.itertuples(index=False, name=None)
            )

        participants_sessions = apply_analysis_level(
            participants_sessions=participants_sessions,
            analysis_level=self.pipeline_step_config.ANALYSIS_LEVEL,
        )

        if self.write_subcohort is not None:
            if not self.dry_run:
                pd.DataFrame(participants_sessions).to_csv(
                    self.write_subcohort, header=False, index=False, sep="\t"
                )
        elif self.hpc:
            self._submit_hpc_job(participants_sessions)
        else:
            n_success, n_total, run_single_results = self.executor.execute_participants_sessions(
                self.run_single, participants_sessions
            )
            
            self.n_success += n_success
            self.n_total += n_total
            self.run_single_results = run_single_results

            # update return code if needed
            if (self.n_success != self.n_total) and (self.n_total != 0):
                self.return_code = ReturnCode.PARTIAL_SUCCESS

    def _generate_cli_command_for_hpc(
        self, participant_id=None, session_id=None
    ) -> list[str]:
        """Generate the CLI command to be run on the HPC cluster."""
        raise NotImplementedError("This method should be implemented in a subclass")

    def _check_hpc_config(self) -> dict:
        """
        Get HPC configuration values to be passed to Jinja template.

        This method is maintained for backward compatibility.
        It delegates to the hpc_submitter's check_hpc_config.
        """
        return self.hpc_submitter.check_hpc_config()

    def _submit_hpc_job(self, participants_sessions):
        """Submit jobs to a HPC cluster for processing.
        
        This method is maintained for backward compatibility.
        It delegates to the hpc_submitter's submit_hpc_job.
        """
        n_jobs_submitted = self.hpc_submitter.submit_hpc_job(
            hpc_type=self.hpc,
            participants_sessions=participants_sessions,
            pipeline_name=self.pipeline_name,
            pipeline_version=self.pipeline_version,
            pipeline_step=self.pipeline_step,
            dpath_work=self.dpath_pipeline_work,
            participant_id=self.participant_id,
            session_id=self.session_id,
            generate_command_func=self._generate_cli_command_for_hpc,
        )
        
        # Update counts for logging in run_cleanup()
        self.n_total += n_jobs_submitted
        self.n_success += n_jobs_submitted

    def run_cleanup(self):
        """Log a summary message."""
        if self.write_subcohort:
            self.logger.success(f"Wrote subcohort to {self.write_subcohort}")
        elif self.n_total == 0:
            self.logger.warning(
                "No participants or sessions to run. Make sure there are no mistakes "
                "in the input arguments, the dataset's manifest or config file, and/or "
                f"check the curation status file at {self.layout.fpath_curation_status}"
            )
            self.return_code = ReturnCode.NO_PARTICIPANTS_OR_SESSIONS_TO_RUN
        elif self.hpc is not None:
            if self.n_success == 0:
                self.logger.error(f"[{LogColor.FAILURE}]Failed to submit HPC jobs[/]")
            else:
                self.logger.info(
                    f"[{LogColor.SUCCESS}]Successfully submitted {self.n_success} "
                    "HPC job(s)[/]"
                )
        else:
            if self.pipeline_step_config.ANALYSIS_LEVEL == AnalysisLevelType.group:
                log_msg = "Ran on the entire study"
            else:
                log_msg = (
                    f"Ran for {self.n_success} out of "
                    f"{self.n_total} participants or sessions"
                )

            if self.n_success == 0:
                self.logger.error(log_msg)
            elif self.n_success == self.n_total:
                self.logger.success(log_msg)
            else:
                self.logger.warning(log_msg)

        return super().run_cleanup()

    @abstractmethod
    def get_participants_sessions_to_run(
        self, participant_id: Optional[str], session_id: Optional[str]
    ):
        """
        Return participant-session pairs to loop over with run_single().

        This is an abstract method that should be defined explicitly in subclasses.
        """

    @abstractmethod
    def run_single(self, participant_id: Optional[str], session_id: Optional[str]):
        """
        Run on a single participant/session.

        This is an abstract method that should be defined explicitly in subclasses.
        """

    def generate_fpath_log(
        self,
        dnames_parent: Optional[str | list[str]] = None,
        fname_stem: Optional[str] = None,
    ) -> Path:
        """Generate a log file path."""
        # make sure that pipeline version is not None
        self.check_pipeline_version()
        if dnames_parent is None:
            dnames_parent = get_pipeline_tag(
                pipeline_name=self.pipeline_name,
                pipeline_version=self.pipeline_version,
            )
        if fname_stem is None:
            fname_stem = get_pipeline_tag(
                pipeline_name=self.pipeline_name,
                pipeline_version=self.pipeline_version,
                participant_id=self.participant_id,
                session_id=self.session_id,
            )
        return super().generate_fpath_log(
            dnames_parent=dnames_parent, fname_stem=fname_stem
        )
