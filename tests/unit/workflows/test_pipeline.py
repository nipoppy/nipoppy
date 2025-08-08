"""Tests for BasePipelineWorkflow."""

import json
import re
from contextlib import nullcontext
from pathlib import Path
from typing import Optional

import pytest
import pytest_mock
from fids import fids
from jinja2 import Environment, meta

from nipoppy.config.boutiques import BoutiquesConfig
from nipoppy.config.hpc import HpcConfig
from nipoppy.config.pipeline import (
    BidsPipelineConfig,
    ExtractionPipelineConfig,
    ProcPipelineConfig,
)
from nipoppy.config.pipeline_step import AnalysisLevelType, ProcPipelineStepConfig
from nipoppy.config.tracker import TrackerConfig
from nipoppy.env import (
    BIDS_SESSION_PREFIX,
    CURRENT_SCHEMA_VERSION,
    DEFAULT_PIPELINE_STEP_NAME,
    FAKE_SESSION_ID,
    ReturnCode,
)
from nipoppy.utils import DPATH_HPC, FPATH_HPC_TEMPLATE, get_pipeline_tag
from nipoppy.workflows.pipeline import (
    BasePipelineWorkflow,
    apply_analysis_level,
    get_pipeline_version,
)
from tests.conftest import datetime_fixture  # noqa F401
from tests.conftest import (
    create_empty_dataset,
    create_pipeline_config_files,
    get_config,
    prepare_dataset,
)


class PipelineWorkflow(BasePipelineWorkflow):
    """Dummy pipeline workflow for testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="test", **kwargs)

    def get_participants_sessions_to_run(
        self, participant_id: Optional[str], session_id: Optional[str]
    ):
        """Only run on participant_id/sessions with BIDS data."""
        return self.curation_status_table.get_bidsified_participants_sessions(
            participant_id=participant_id, session_id=session_id
        )

    def run_single(self, participant_id: str, session_id: str):
        """Run on a single participant_id/session_id."""
        self.logger.info(f"Running on {participant_id}, {session_id}")
        if participant_id == "FAIL":
            raise RuntimeError("FAIL")


@pytest.fixture(scope="function")
def workflow(tmp_path: Path):
    workflow = PipelineWorkflow(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
        pipeline_step=DEFAULT_PIPELINE_STEP_NAME,
    )

    # write config
    config = get_config()
    config.save(workflow.layout.fpath_config)

    create_empty_dataset(workflow.layout.dpath_root)

    create_pipeline_config_files(
        workflow.layout.dpath_pipelines,
        bidsification_pipelines=[
            {
                "NAME": "bids_converter",
                "VERSION": "1.0",
                "CONTAINER_INFO": {"FILE": "path"},
                "STEPS": [{"NAME": "step1"}, {"NAME": "step2"}],
            },
            {
                "NAME": "bids_converter",
                "VERSION": "0.1",
            },
        ],
        processing_pipelines=[
            {
                "NAME": "fmriprep",
                "VERSION": "23.1.3",
                "STEPS": [{}],
            },
            {
                "NAME": "my_pipeline",
                "VERSION": "1.0",
                "CONTAINER_INFO": {
                    "FILE": "[[NIPOPPY_DPATH_CONTAINERS]]/my_container.sif"
                },
                "STEPS": [{}],
            },
            {
                "NAME": "my_pipeline",
                "VERSION": "2.0",
                "STEPS": [{}],
            },
        ],
        extraction_pipelines=[
            {
                "NAME": "extractor1",
                "VERSION": "0.1.0",
                "PROC_DEPENDENCIES": [{"NAME": "pipeline1", "VERSION": "v1"}],
            },
        ],
    )
    return workflow


def _set_up_hpc_for_testing(
    workflow: PipelineWorkflow, mocker: pytest_mock.MockFixture
):
    # set HPC attribute to something valid
    workflow.hpc = "slurm"

    # copy HPC config files
    workflow.copytree(DPATH_HPC, workflow.layout.dpath_hpc)

    # mock PySQA job submission function
    mock_submit_job = mocker.patch("pysqa.QueueAdapter.submit_job")

    mocker.patch.object(
        workflow,
        "_generate_cli_command_for_hpc",
        side_effect=(
            lambda participant_id, session_id: [
                "echo",
                f"{participant_id}, {session_id}",
            ]
        ),
    )

    return mock_submit_job


def _set_up_substitution_testing(
    workflow: PipelineWorkflow, mocker: pytest_mock.MockerFixture
):
    return mocker.patch.object(
        workflow, "process_template_json", side_effect=workflow.process_template_json
    )


@pytest.mark.parametrize(
    "analysis_level,expected",
    [
        (
            AnalysisLevelType.participant_session,
            [("S01", "BL"), ("S01", "FU"), ("S02", "BL"), ("S02", "FU")],
        ),
        (AnalysisLevelType.participant, [("S01", None), ("S02", None)]),
        (AnalysisLevelType.session, [(None, "BL"), (None, "FU")]),
        (AnalysisLevelType.group, [(None, None)]),
    ],
)
def test_apply_analysis_level(analysis_level, expected):
    participants_sessions = [("S01", "BL"), ("S01", "FU"), ("S02", "BL"), ("S02", "FU")]
    assert apply_analysis_level(participants_sessions, analysis_level) == expected


@pytest.mark.parametrize(
    "dname_pipelines,pipeline_name,expected_version",
    [
        ("processing", "fmriprep", "23.1.3"),
        ("processing", "my_pipeline", "2.0"),
        ("bidsification", "bids_converter", "1.0"),
        ("extraction", "extractor1", "0.1.0"),
    ],
)
def test_get_pipeline_version(
    dname_pipelines: str,
    pipeline_name: str,
    expected_version: str,
    workflow: BasePipelineWorkflow,
):
    assert (
        get_pipeline_version(
            pipeline_name, workflow.layout.dpath_pipelines / dname_pipelines
        )
        == expected_version
    )


def test_get_pipeline_version_invalid_name(tmp_path: Path):
    with pytest.raises(ValueError, match="No config found for pipeline"):
        get_pipeline_version("pipeline1", tmp_path)


@pytest.mark.parametrize(
    "args",
    [
        {
            "dpath_root": "my_dataset",
            "pipeline_name": "my_pipeline",
            "pipeline_version": "1.0",
        },
        {
            "dpath_root": "my_dataset",
            "pipeline_name": "my_other_pipeline",
            "pipeline_version": "2.0",
        },
    ],
)
def test_init(args):
    workflow = PipelineWorkflow(**args)
    assert isinstance(workflow, BasePipelineWorkflow)
    assert hasattr(workflow, "pipeline_name")
    assert hasattr(workflow, "pipeline_version")
    assert hasattr(workflow, "pipeline_step")
    assert hasattr(workflow, "participant_id")
    assert hasattr(workflow, "session_id")
    assert isinstance(workflow.dpath_pipeline, Path)
    assert isinstance(workflow.dpath_pipeline_output, Path)
    assert isinstance(workflow.dpath_pipeline_work, Path)
    assert isinstance(workflow.dpath_pipeline_bids_db, Path)


@pytest.mark.parametrize(
    "participant_id,session_id,participant_expected,session_expected",
    [
        ("01", "BL", "01", "BL"),
        ("sub-01", "ses-BL", "01", "BL"),
    ],
)
def test_init_participant_session(
    participant_id, session_id, participant_expected, session_expected
):
    workflow = PipelineWorkflow(
        dpath_root="my_dataset",
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
        participant_id=participant_id,
        session_id=session_id,
    )
    assert workflow.participant_id == participant_expected
    assert workflow.session_id == session_expected


def test_pipeline_version_optional():
    workflow = PipelineWorkflow(
        dpath_root="my_dataset",
        pipeline_name="my_pipeline",
    )
    assert workflow.pipeline_version is None


def test_pipeline_config(workflow: PipelineWorkflow, mocker: pytest_mock.MockFixture):
    mocked_process_template_json = _set_up_substitution_testing(workflow, mocker)

    assert isinstance(workflow.pipeline_config, ProcPipelineConfig)

    # make sure substitutions are processed
    mocked_process_template_json.assert_called_once()


def test_fpath_container(workflow: PipelineWorkflow):
    fpath_container = workflow.layout.dpath_containers / "my_container.sif"
    fpath_container.parent.mkdir(parents=True, exist_ok=True)
    fpath_container.touch()
    assert isinstance(workflow.fpath_container, Path)


def test_fpath_container_custom(workflow: PipelineWorkflow):
    fpath_custom = workflow.dpath_root / "my_container.sif"
    workflow.pipeline_config.CONTAINER_INFO.FILE = fpath_custom
    fpath_custom.touch()
    assert isinstance(workflow.fpath_container, Path)


def test_fpath_container_not_specified(workflow: PipelineWorkflow):
    workflow.pipeline_config.CONTAINER_INFO.FILE = None
    with pytest.raises(RuntimeError, match="No container image file specified"):
        workflow.fpath_container


@pytest.mark.parametrize("container_uri", [None, "docker://some/uri:tag"])
def test_fpath_container_not_found(workflow: PipelineWorkflow, container_uri):
    workflow.pipeline_config.CONTAINER_INFO.URI = container_uri
    error_message = (
        "No container image file found at "
        f"{workflow.pipeline_config.CONTAINER_INFO.FILE} for pipeline "
        f"{workflow.pipeline_name} {workflow.pipeline_version}"
    )
    if container_uri is not None:
        error_message += (
            ". This file can be downloaded to the appropriate path by running the "
            "following command:\n\n"
            f"apptainer pull {workflow.pipeline_config.CONTAINER_INFO.FILE}"
            f" {workflow.pipeline_config.CONTAINER_INFO.URI}"
        )
    with pytest.raises(FileNotFoundError, match=error_message):
        workflow.fpath_container


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,pipeline_step,descriptor",
    [
        ("fmriprep", "23.1.3", None, {}),
        ("my_pipeline", "1.0", None, {"key2": "value2"}),
    ],
)
def test_descriptor(
    workflow: PipelineWorkflow,
    pipeline_name,
    pipeline_version,
    pipeline_step,
    descriptor,
    tmp_path: Path,
):
    workflow.pipeline_name = pipeline_name
    workflow.pipeline_version = pipeline_version
    workflow.pipeline_step = pipeline_step

    fpath_descriptor = tmp_path / "descriptor.json"
    fpath_descriptor.write_text(json.dumps(descriptor))

    workflow.pipeline_step_config.DESCRIPTOR_FILE = fpath_descriptor.name
    workflow.dpath_pipeline_bundle = fpath_descriptor.parent
    assert workflow.descriptor == descriptor


def test_descriptor_none(workflow: PipelineWorkflow):
    with pytest.raises(ValueError, match="No descriptor file specified for pipeline"):
        workflow.descriptor


@pytest.mark.parametrize(
    "variables,expected_descriptor",
    [
        ({"TO_REPLACE1": "value1"}, {"key1": "value1"}),
        ({"[[TO_REPLACE1]]": "value1"}, {"key1": "[[TO_REPLACE1]]"}),
    ],
)
def test_descriptor_pipeline_variables(
    tmp_path: Path, workflow: PipelineWorkflow, variables, expected_descriptor
):
    # set variables for substitution
    workflow.config.PIPELINE_VARIABLES.PROCESSING[workflow.pipeline_name][
        workflow.pipeline_version
    ] = variables

    # set descriptor file and write descriptor content
    fpath_descriptor = tmp_path / "descriptor.json"
    fpath_descriptor.write_text(json.dumps({"key1": "[[TO_REPLACE1]]"}))

    workflow.pipeline_step_config.DESCRIPTOR_FILE = fpath_descriptor.name
    workflow.dpath_pipeline_bundle = fpath_descriptor.parent

    assert workflow.descriptor == expected_descriptor


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,invocation",
    [
        ("my_pipeline", "1.0", {"key1": "val1", "key2": "val2"}),
        ("fmriprep", "23.1.3", {}),
    ],
)
def test_invocation(
    pipeline_name,
    pipeline_version,
    invocation,
    tmp_path: Path,
    workflow: PipelineWorkflow,
):
    workflow.pipeline_name = pipeline_name
    workflow.pipeline_version = pipeline_version

    fpath_invocation = tmp_path / "invocation.json"
    fpath_invocation.write_text(json.dumps(invocation))

    workflow.pipeline_step_config.INVOCATION_FILE = fpath_invocation.name
    workflow.dpath_pipeline_bundle = fpath_invocation.parent

    assert workflow.invocation == invocation


def test_invocation_none(workflow: PipelineWorkflow):
    with pytest.raises(ValueError, match="No invocation file specified for pipeline"):
        workflow.invocation


@pytest.mark.parametrize(
    "variables,expected_invocation",
    [
        ({"TO_REPLACE1": "value1"}, {"key1": "value1"}),
        ({"[[TO_REPLACE1]]": "value1"}, {"key1": "[[TO_REPLACE1]]"}),
    ],
)
def test_invocation_pipeline_variables(
    tmp_path: Path, workflow: PipelineWorkflow, variables, expected_invocation
):
    # set variables for substitution
    workflow.config.PIPELINE_VARIABLES.PROCESSING[workflow.pipeline_name][
        workflow.pipeline_version
    ] = variables

    # set invocation file and write invocation content
    fpath_invocation = tmp_path / "invocation.json"
    fpath_invocation.write_text(json.dumps({"key1": "[[TO_REPLACE1]]"}))

    workflow.pipeline_step_config.INVOCATION_FILE = fpath_invocation.name
    workflow.dpath_pipeline_bundle = fpath_invocation.parent

    assert workflow.invocation == expected_invocation


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,pipeline_step,tracker_config_data",
    [
        ("fmriprep", "23.1.3", None, {"PATHS": ["path1"]}),
        ("my_pipeline", "1.0", None, {"PATHS": ["path1", "path2"]}),
    ],
)
def test_tracker_config(
    workflow: PipelineWorkflow,
    pipeline_name,
    pipeline_version,
    pipeline_step,
    tracker_config_data,
    tmp_path: Path,
):
    workflow.pipeline_name = pipeline_name
    workflow.pipeline_version = pipeline_version
    workflow.pipeline_step = pipeline_step

    fpath_tracker_config = tmp_path / "tracker_config.json"
    fpath_tracker_config.write_text(json.dumps(tracker_config_data))

    workflow.pipeline_step_config.TRACKER_CONFIG_FILE = fpath_tracker_config.name
    workflow.dpath_pipeline_bundle = fpath_tracker_config.parent
    assert workflow.tracker_config == TrackerConfig(**tracker_config_data)


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,patterns",
    [
        ("my_pipeline", "1.0", ["PATTERN1", "PATTERN2"]),
        ("fmriprep", "23.1.3", ["PATTERN3", "PATTERN4"]),
    ],
)
def test_pybids_ignore_patterns(
    pipeline_name,
    pipeline_version,
    patterns,
    tmp_path: Path,
    workflow: PipelineWorkflow,
):
    workflow.pipeline_name = pipeline_name
    workflow.pipeline_version = pipeline_version

    fpath_patterns = tmp_path / "pybids_ignore_patterns.json"
    fpath_patterns.write_text(json.dumps(patterns))

    workflow.pipeline_step_config.PYBIDS_IGNORE_FILE = fpath_patterns.name
    workflow.dpath_pipeline_bundle = fpath_patterns.parent

    assert workflow.pybids_ignore_patterns == [
        re.compile(pattern) for pattern in patterns
    ]


def test_pybids_ignore_patterns_no_file(workflow: PipelineWorkflow):
    workflow.pipeline_step_config.PYBIDS_IGNORE_FILE = None
    assert workflow.pybids_ignore_patterns == []


def test_pybids_ignore_patterns_invalid_format(
    workflow: PipelineWorkflow, tmp_path: Path
):
    fpath_patterns = tmp_path / "pybids_ignore_patterns.json"
    fpath_patterns.write_text(json.dumps({"key": "value"}))
    workflow.pipeline_step_config.PYBIDS_IGNORE_FILE = fpath_patterns

    with pytest.raises(ValueError, match="Expected a list of strings"):
        workflow.pybids_ignore_patterns


@pytest.mark.parametrize("hpc_config_data", [{}, {"CORES": "8", "MEMORY": "32G"}])
def test_hpc_config(
    hpc_config_data: dict,
    workflow: PipelineWorkflow,
    tmp_path: Path,
    mocker: pytest_mock.MockFixture,
):
    fpath_hpc_config = tmp_path / "hpc_config.json"
    fpath_hpc_config.write_text(json.dumps(hpc_config_data))

    workflow.pipeline_step_config.HPC_CONFIG_FILE = fpath_hpc_config.name
    workflow.dpath_pipeline_bundle = fpath_hpc_config.parent

    mocked_process_template_json = _set_up_substitution_testing(workflow, mocker)

    assert isinstance(workflow.hpc_config, HpcConfig)

    # make sure substitutions are processed
    mocked_process_template_json.assert_called_once()


def test_hpc_config_no_file(workflow: PipelineWorkflow):
    workflow.pipeline_step_config.HPC_CONFIG_FILE = None
    assert workflow.hpc_config == HpcConfig()


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,dname_pipelines,pipeline_class",
    [
        ("fmriprep", "23.1.3", "processing", ProcPipelineConfig),
        ("my_pipeline", "2.0", "processing", ProcPipelineConfig),
        ("bids_converter", "1.0", "bidsification", BidsPipelineConfig),
        ("extractor1", "0.1.0", "extraction", ExtractionPipelineConfig),
    ],
)
def test_get_pipeline_config(
    pipeline_name,
    pipeline_version,
    dname_pipelines,
    pipeline_class,
    workflow: PipelineWorkflow,
):
    dpath_pipeline_bundle = (
        workflow.layout.dpath_pipelines
        / dname_pipelines
        / f"{pipeline_name}-{pipeline_version}"
    )
    assert isinstance(
        workflow._get_pipeline_config(
            dpath_pipeline_bundle,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            pipeline_class=pipeline_class,
        ),
        pipeline_class,
    )


def test_get_pipeline_config_invalid(workflow: PipelineWorkflow):
    pipeline_name = "new_pipeline"
    pipeline_version = "1.0.0"
    dpath_pipeline_bundle = (
        workflow.layout.dpath_pipelines
        / "processing"
        / f"{pipeline_name}-{pipeline_version}"
    )
    config_dict = {
        "NAME": pipeline_name,
        "VERSION": "2.0.0",  # different version
        "PIPELINE_TYPE": "processing",
        "SCHEMA_VERSION": CURRENT_SCHEMA_VERSION,
    }
    dpath_pipeline_bundle.mkdir(parents=True)
    (dpath_pipeline_bundle / "config.json").write_text(json.dumps(config_dict))
    with pytest.raises(
        RuntimeError,
        match=(
            "Expected pipeline config to have "
            f'NAME="{pipeline_name}" and VERSION="{pipeline_version}"'
        ),
    ):
        workflow._get_pipeline_config(
            dpath_pipeline_bundle,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            pipeline_class=ProcPipelineConfig,
        )


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,dname_pipelines,pipeline_class",
    [
        ("not_a_pipeline", "23.1.3", "processing", ProcPipelineConfig),
        ("my_pipeline", "not_a_version", "processing", ProcPipelineConfig),
        ("bids_converter", "2.0", "bidsification", BidsPipelineConfig),
        ("bids_converter", "1.0", "extraction", ExtractionPipelineConfig),
    ],
)
def test_get_pipeline_config_missing(
    pipeline_name,
    pipeline_version,
    dname_pipelines,
    pipeline_class,
    workflow: PipelineWorkflow,
):
    dpath_pipeline_bundle = (
        workflow.layout.dpath_pipelines
        / dname_pipelines
        / f"{pipeline_name}-{pipeline_version}"
    )
    with pytest.raises(FileNotFoundError, match="Pipeline config file not found at"):
        workflow._get_pipeline_config(
            dpath_pipeline_bundle,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            pipeline_class=pipeline_class,
        )


@pytest.mark.parametrize("return_str", [True, False])
def test_process_template_json(workflow: PipelineWorkflow, return_str):
    # add user-defined substitution variables
    workflow.config.SUBSTITUTIONS = {
        "USER_SUBSTITUTION": "val1",
        "OTHER_USER_SUBSTITUTION": "val2",
    }

    class Test:
        extra2 = "extra_obj_attribute"

    processed = workflow.process_template_json(
        {
            "[[NIPOPPY_BIDS_PARTICIPANT_ID]]": "[[NIPOPPY_PARTICIPANT_ID]]",
            "[[NIPOPPY_BIDS_SESSION_ID]]": "[[NIPOPPY_SESSION_ID]]",
            "[[NIPOPPY_DPATH_PIPELINE]]": "[[NIPOPPY_DPATH_BIDS]]",
            "[[NIPOPPY_EXTRA1]]": "[[NIPOPPY_EXTRA2]]",
            "USER_SUBSTITUTION": "OTHER_USER_SUBSTITUTION",
        },
        participant_id="01",
        session_id="1",
        extra1="extra_kwarg",
        objs=[Test()],
        return_str=return_str,
    )

    if return_str:
        assert isinstance(processed, str)
    else:
        assert isinstance(processed, dict)
        processed = json.dumps(processed)

    # check that everything was replaced
    for pattern in [
        "[[NIPOPPY_BIDS_PARTICIPANT_ID]]",
        "[[NIPOPPY_PARTICIPANT_ID]]",
        "[[NIPOPPY_BIDS_SESSION_ID]]",
        "[[NIPOPPY_SESSION_ID]]",
        "[[NIPOPPY_DPATH_PIPELINE]]",
        "[[NIPOPPY_DPATH_BIDS]]",
        "[[NIPOPPY_EXTRA1]]",
        "[[NIPOPPY_EXTRA2]]",
        "USER_SUBSTITUTION",
        "OTHER_USER_SUBSTITUTION",
    ]:
        assert pattern not in processed


def test_boutiques_config(tmp_path: Path):
    workflow = PipelineWorkflow(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
    )
    workflow.descriptor = {
        "custom": {
            "nipoppy": {"CONTAINER_CONFIG": {"ARGS": ["--pipeline-specific-arg"]}}
        }
    }

    boutiques_config = workflow.boutiques_config
    assert isinstance(boutiques_config, BoutiquesConfig)
    # should not be the default
    assert boutiques_config != BoutiquesConfig()


def test_boutiques_config_default(tmp_path: Path):
    workflow = PipelineWorkflow(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="no_boutiques_config",
        pipeline_version="1.0",
    )
    workflow.descriptor = {}
    boutiques_config = workflow.boutiques_config
    assert isinstance(boutiques_config, BoutiquesConfig)
    # expect the default
    assert boutiques_config == BoutiquesConfig()


def test_boutiques_config_invalid(tmp_path: Path):
    workflow = PipelineWorkflow(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="bad_boutiques_config",
        pipeline_version="1.0",
    )
    workflow.descriptor = {"custom": {"nipoppy": {"INVALID_ARG": "value"}}}

    with pytest.raises(ValueError, match="Error when loading the Boutiques config"):
        workflow.boutiques_config


@pytest.mark.parametrize(
    "participant_id,session_id,expected_count",
    [
        (None, None, 12),
        ("01", None, 6),
        ("02", None, 6),
        (None, "1", 5),
        (None, "2", 5),
        (None, "3", 2),
        ("01", "3", 2),
        ("02", "3", 0),
    ],
)
def test_set_up_bids_db(
    workflow: PipelineWorkflow,
    participant_id,
    session_id,
    expected_count,
    tmp_path: Path,
):
    dpath_pybids_db = tmp_path / "bids_db"
    fids.create_fake_bids_dataset(
        output_dir=workflow.layout.dpath_bids,
        subjects="01",
        sessions=["1", "2", "3"],
        datatypes=["anat"],
    )
    fids.create_fake_bids_dataset(
        output_dir=workflow.layout.dpath_bids,
        subjects="02",
        sessions=["1", "2"],
        datatypes=["anat", "func"],
    )
    bids_layout = workflow.set_up_bids_db(
        dpath_pybids_db=dpath_pybids_db,
        participant_id=participant_id,
        session_id=session_id,
    )
    assert dpath_pybids_db.exists()
    assert len(bids_layout.get(extension=".nii.gz")) == expected_count


def test_set_up_bids_db_ignore_patterns(workflow: PipelineWorkflow, tmp_path: Path):
    dpath_pybids_db = tmp_path / "bids_db"
    participant_id = "01"
    session_id = "1"

    fids.create_fake_bids_dataset(
        output_dir=workflow.layout.dpath_bids,
    )

    pybids_ignore_patterns = workflow.pybids_ignore_patterns[:]

    workflow.set_up_bids_db(
        dpath_pybids_db=dpath_pybids_db,
        participant_id=participant_id,
        session_id=session_id,
    )

    assert pybids_ignore_patterns == workflow.pybids_ignore_patterns


def test_set_up_bids_db_no_session(
    workflow: PipelineWorkflow,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
):
    """Create a fake BIDS dataset with no session-level folders.

    Make sure:
    - Check that the ignore pattern is not added to the BIDS layout.
    - Check if files are found in the BIDS layout not ignored.
    """
    dpath_pybids_db = tmp_path / "bids_db"
    participant_id = "01"
    session_id = FAKE_SESSION_ID

    fids.create_fake_bids_dataset(
        output_dir=workflow.layout.dpath_bids,
        subjects=participant_id,
        sessions=None,
    )

    bids_layout = workflow.set_up_bids_db(
        dpath_pybids_db=dpath_pybids_db,
        participant_id=participant_id,
        session_id=session_id,
    )

    assert not (f".*?/{BIDS_SESSION_PREFIX}(?!{session_id})" in caplog.text)
    assert len(bids_layout.get(extension=".nii.gz")) > 0


@pytest.mark.parametrize(
    "pipeline_name,expected_version",
    [("fmriprep", "23.1.3"), ("my_pipeline", "2.0")],
)
def test_check_pipeline_version(
    pipeline_name,
    expected_version,
    workflow: PipelineWorkflow,
    caplog: pytest.LogCaptureFixture,
):
    workflow.pipeline_name = pipeline_name
    workflow.pipeline_version = None  # should be inferred
    workflow.check_pipeline_version()
    assert workflow.pipeline_version == expected_version
    assert f"using version {expected_version}" in caplog.text


@pytest.mark.parametrize(
    "variables,valid", [({"var1": "val1"}, True), ({"var2": None}, False)]
)
def test_check_pipeline_variables(workflow: PipelineWorkflow, variables, valid):
    workflow.config.PIPELINE_VARIABLES.PROCESSING[workflow.pipeline_name][
        workflow.pipeline_version
    ] = variables
    with (
        nullcontext()
        if valid
        else pytest.raises(ValueError, match="Variable .* is not set in the config")
    ):
        assert workflow._check_pipeline_variables() is None


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,expected_step",
    [
        ("fmriprep", "23.1.3", DEFAULT_PIPELINE_STEP_NAME),
        ("my_pipeline", "1.0", DEFAULT_PIPELINE_STEP_NAME),
    ],
)
def test_check_pipeline_step(
    pipeline_name,
    pipeline_version,
    expected_step,
    workflow: PipelineWorkflow,
    caplog: pytest.LogCaptureFixture,
):
    workflow.pipeline_name = pipeline_name
    workflow.pipeline_version = pipeline_version
    workflow.pipeline_step = None
    workflow.check_pipeline_step()
    assert workflow.pipeline_step == expected_step
    assert f"using step {expected_step}" in caplog.text


def test_run_setup_pipeline_version_step(workflow: PipelineWorkflow):
    workflow.pipeline_version = None
    workflow.pipeline_step = None
    create_empty_dataset(workflow.layout.dpath_root)
    workflow.run_setup()
    assert workflow.pipeline_version == "2.0"
    assert workflow.pipeline_step == DEFAULT_PIPELINE_STEP_NAME


@pytest.mark.parametrize("dry_run", [True, False])
def test_run_setup_create_directories(workflow: PipelineWorkflow, dry_run: bool):
    workflow.dry_run = dry_run

    assert len(workflow.dpaths_to_check) == 0
    workflow.dpaths_to_check = [workflow.dpath_pipeline]

    workflow.run_setup()
    assert workflow.dpath_pipeline.exists() == (not dry_run)

    # run again, should not fail even if directories already exist
    workflow.run_setup()


@pytest.mark.parametrize(
    "participant_id,session_id,expected_count",
    [(None, None, 4), ("01", None, 3), ("01", "2", 1)],
)
def test_run_main(
    workflow: PipelineWorkflow,
    participant_id,
    session_id,
    expected_count,
):
    workflow.participant_id = participant_id
    workflow.session_id = session_id

    participants_and_sessions = {"01": ["1", "2", "3"], "02": ["1"]}
    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions,
        participants_and_sessions_bidsified=participants_and_sessions,
        dpath_bidsified=workflow.layout.dpath_bids,
    )
    manifest.save_with_backup(workflow.layout.fpath_manifest)
    workflow.run_main()
    assert workflow.n_total == expected_count
    assert workflow.n_success == expected_count


def test_run_main_analysis_level(
    workflow: PipelineWorkflow,
    mocker: pytest_mock.MockFixture,
):
    mocked = mocker.patch("nipoppy.workflows.pipeline.apply_analysis_level")
    participants_and_sessions = {"01": ["1", "2", "3"], "02": ["1"]}
    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions
    )
    manifest.save_with_backup(workflow.layout.fpath_manifest)
    workflow.run_main()
    assert mocked.call_count == 1


def test_run_main_catch_errors(workflow: PipelineWorkflow):
    workflow.participant_id = "FAIL"
    workflow.session_id = "1"

    participants_and_sessions = {workflow.participant_id: [workflow.session_id]}
    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions,
        participants_and_sessions_bidsified=participants_and_sessions,
        dpath_bidsified=workflow.layout.dpath_bids,
    )
    manifest.save_with_backup(workflow.layout.fpath_manifest)
    workflow.run_main()
    assert workflow.n_total == 1
    assert workflow.n_success == 0
    assert workflow.return_code == ReturnCode.PARTIAL_SUCCESS


@pytest.mark.parametrize("write_list", ["list.tsv", "to_run.tsv"])
@pytest.mark.parametrize("dry_run", [True, False])
def test_run_main_write_list(
    workflow: PipelineWorkflow,
    write_list: str,
    dry_run: bool,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
):
    write_list = tmp_path / write_list

    workflow.participant_id = "01"
    workflow.session_id = "1"
    workflow.write_list = write_list
    workflow.dry_run = dry_run

    participants_and_sessions = {workflow.participant_id: [workflow.session_id]}
    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions,
        participants_and_sessions_bidsified=participants_and_sessions,
        dpath_bidsified=workflow.layout.dpath_bids,
    )
    workflow.manifest = manifest
    workflow.run_main()

    if not dry_run:
        assert write_list.exists()
        assert write_list.read_text().strip() == "01\t1"
    else:
        assert not write_list.exists()
    assert f"Wrote participant-session list to {write_list}" in caplog.text


@pytest.mark.parametrize(
    "n_success,n_total,analysis_level,expected_message",
    [
        (0, 0, "participant_session", "No participants or sessions to run"),
        (
            1,
            2,
            "participant_session",
            "Ran for {0} out of {1} participants or sessions",
        ),
        (
            0,
            1,
            "participant_session",
            "Ran for {0} out of {1} participants or sessions",
        ),
        (
            2,
            2,
            "participant_session",
            "Ran for {0} out of {1} participants or sessions",
        ),
        (
            1,
            1,
            "group",
            "Ran on the entire study",
        ),
    ],
)
def test_run_cleanup(
    n_success,
    n_total,
    analysis_level,
    expected_message: str,
    workflow: PipelineWorkflow,
    caplog: pytest.LogCaptureFixture,
):
    workflow.n_success = n_success
    workflow.n_total = n_total

    workflow.pipeline_config.STEPS = [
        ProcPipelineStepConfig(ANALYSIS_LEVEL=analysis_level)
    ]

    workflow.run_cleanup()

    assert expected_message.format(n_success, n_total) in caplog.text


def test_run_cleanup_no_participants_warning(
    workflow: PipelineWorkflow, caplog: pytest.LogCaptureFixture
):
    workflow.n_success = 0
    workflow.n_total = 0
    workflow.run_cleanup()
    assert any(
        record.levelname == "WARNING"
        and "No participants or sessions to run" in record.message
        for record in caplog.records
    ), "Wrong log message or level"
    assert (
        workflow.return_code == ReturnCode.NO_PARTICIPANTS_OR_SESSIONS_TO_RUN
    ), "Wrong return code"


@pytest.mark.parametrize(
    "n_success,n_total,expected_message",
    [
        (0, 0, "No participants or sessions to run"),
        (0, 1, "[red]Failed to submit HPC jobs[/]"),
        (2, 2, "[green]Successfully submitted 2 HPC job(s)[/]"),
    ],
)
def test_run_cleanup_hpc(
    n_success,
    n_total,
    expected_message,
    workflow: PipelineWorkflow,
    caplog: pytest.LogCaptureFixture,
):
    workflow.hpc = "slurm"

    workflow.n_success = n_success
    workflow.n_total = n_total
    workflow.run_cleanup()

    assert expected_message in caplog.text


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,participant_id,session_id,expected_stem",
    [
        (
            "my_pipeline",
            "1.0",
            "sub1",
            None,
            "test/my_pipeline-1.0/my_pipeline-1.0-sub1",
        ),
        (
            "my_pipeline",
            None,
            "sub1",
            None,
            "test/my_pipeline-2.0/my_pipeline-2.0-sub1",
        ),
        ("fmriprep", None, None, "1", "test/fmriprep-23.1.3/fmriprep-23.1.3-1"),
    ],
)
def test_generate_fpath_log(
    pipeline_name,
    pipeline_version,
    participant_id,
    session_id,
    expected_stem,
    workflow: PipelineWorkflow,
    datetime_fixture,  # noqa F811
):
    workflow.pipeline_name = pipeline_name
    workflow.pipeline_version = pipeline_version
    workflow.participant_id = participant_id
    workflow.session_id = session_id
    fpath_log = workflow.generate_fpath_log()
    assert (
        fpath_log == workflow.layout.dpath_logs / f"{expected_stem}-20240404_1234.log"
    )


@pytest.mark.parametrize(
    "hpc_config_data", [{"CORES": "8", "MEMORY": "32G"}, {"ACCOUNT": "my_account"}]
)
def test_check_hpc_config(hpc_config_data, workflow: PipelineWorkflow):
    workflow.hpc_config = HpcConfig(**hpc_config_data)
    assert workflow._check_hpc_config() == hpc_config_data


def test_check_hpc_config_empty(
    workflow: PipelineWorkflow,
    caplog: pytest.LogCaptureFixture,
):
    workflow.hpc_config = HpcConfig()
    workflow._check_hpc_config()
    assert (
        sum(
            [
                (
                    "HPC configuration is empty" in record.message
                    and record.levelname == "WARNING"
                )
                for record in caplog.records
            ]
        )
        == 1
    )


def test_check_hpc_config_unused_vars(
    workflow: PipelineWorkflow, caplog: pytest.LogCaptureFixture
):
    workflow.hpc_config = HpcConfig(CORES="8", RANDOM_VAR="value")
    workflow._check_hpc_config()
    assert sum(
        [
            (
                (
                    "Found variables in the HPC config that are not used"
                    in record.message
                )
                and ("RANDOM_VAR" in record.message)
                and record.levelname == "WARNING"
            )
            for record in caplog.records
        ]
    )


def test_submit_hpc_job_no_dir(workflow: PipelineWorkflow):
    assert not workflow.layout.dpath_hpc.exists()
    with pytest.raises(
        FileNotFoundError,
        match="The HPC directory with appropriate content needs to exist",
    ):
        workflow._submit_hpc_job([("P1", "1")])


def test_submit_hpc_job_invalid_hpc(
    workflow: PipelineWorkflow, mocker: pytest_mock.MockFixture
):
    _set_up_hpc_for_testing(workflow, mocker)
    workflow.hpc = "invalid"

    with pytest.raises(ValueError, match="Invalid HPC cluster type"):
        workflow._submit_hpc_job([("P1", "1")])


def test_submit_hpc_job_logs(
    workflow: PipelineWorkflow, mocker: pytest_mock.MockFixture
):
    _set_up_hpc_for_testing(workflow, mocker)

    dpath_logs = workflow.layout.dpath_logs / workflow.dname_hpc_logs

    # check that logs directory is created
    assert not (dpath_logs).exists()
    workflow._submit_hpc_job([("P1", "1")])
    assert dpath_logs.exists()


def test_submit_hpc_job_no_jobs(
    workflow: PipelineWorkflow, mocker: pytest_mock.MockFixture
):
    mocked = _set_up_hpc_for_testing(workflow, mocker)
    workflow._submit_hpc_job([])
    assert not mocked.called


@pytest.mark.parametrize("hpc_type", ["slurm", "sge"])
def test_submit_hpc_job_pysqa_call(
    workflow: PipelineWorkflow,
    mocker: pytest_mock.MockFixture,
    hpc_type,
):
    preamble_list = ["module load some module"]
    hpc_config = {
        "CORES": "8",
        "MEMORY": "32G",
    }

    mocked_submit_job = _set_up_hpc_for_testing(workflow, mocker)
    workflow.hpc = hpc_type

    workflow.hpc_config = HpcConfig(**hpc_config)
    workflow.config.HPC_PREAMBLE = preamble_list

    participants_sessions = [("participant1", "session1"), ("participant2", "session2")]

    # Call the function we're testing
    workflow._submit_hpc_job(participants_sessions)

    # Extract the arguments passed to submit_job
    submit_job_args = mocked_submit_job.call_args[1]

    # Verify args
    assert submit_job_args["queue"] == hpc_type
    assert submit_job_args["working_directory"] == str(workflow.dpath_pipeline_work)
    assert submit_job_args["NIPOPPY_HPC"] == hpc_type
    assert submit_job_args["NIPOPPY_JOB_NAME"] == get_pipeline_tag(
        workflow.pipeline_name,
        workflow.pipeline_version,
        workflow.pipeline_step,
        workflow.participant_id,
        workflow.session_id,
    )
    assert (
        submit_job_args["NIPOPPY_DPATH_LOGS"]
        == workflow.layout.dpath_logs / workflow.dname_hpc_logs
    )
    assert submit_job_args["NIPOPPY_HPC_PREAMBLE_STRINGS"] == preamble_list

    assert submit_job_args["NIPOPPY_DPATH_ROOT"] == workflow.layout.dpath_root
    assert submit_job_args["NIPOPPY_PIPELINE_NAME"] == workflow.pipeline_name
    assert submit_job_args["NIPOPPY_PIPELINE_VERSION"] == workflow.pipeline_version
    assert submit_job_args["NIPOPPY_PIPELINE_STEP"] == workflow.pipeline_step

    submitted_participant_ids = submit_job_args["NIPOPPY_PARTICIPANT_IDS"]
    submitted_session_ids = submit_job_args["NIPOPPY_SESSION_IDS"]
    assert len(submitted_participant_ids) == len(participants_sessions)
    assert len(submitted_session_ids) == len(participants_sessions)
    assert set(zip(submitted_participant_ids, submitted_session_ids)) == set(
        participants_sessions
    )

    command_list = submit_job_args["NIPOPPY_COMMANDS"]
    assert len(command_list) == len(participants_sessions)
    for participant_id, session_id in participants_sessions:
        assert (f"echo '{participant_id}, {session_id}'") in command_list

    for key, value in hpc_config.items():
        assert submit_job_args.get(key) == value

    template_ast = Environment().parse(FPATH_HPC_TEMPLATE.read_text())
    template_vars = meta.find_undeclared_variables(template_ast)
    nipoppy_args = [arg for arg in submit_job_args.keys() if arg.startswith("NIPOPPY_")]
    for arg in nipoppy_args:
        assert arg in template_vars, f"Variable {arg} not found in the template"

    assert workflow.n_success == 2
    assert workflow.n_total == 2


@pytest.mark.parametrize(
    "write_job_script,expected_message",
    [(True, "Job script created at "), (False, "No job script found at ")],
)
def test_submit_hpc_job_job_script(
    write_job_script: bool,
    expected_message,
    workflow: PipelineWorkflow,
    mocker: pytest_mock.MockFixture,
    caplog: pytest.LogCaptureFixture,
):
    def touch_job_script(*args, **kwargs):
        fpath_script = workflow.dpath_pipeline_work / "run_queue.sh"
        fpath_script.parent.mkdir(parents=True, exist_ok=True)
        fpath_script.touch()

    mocked = _set_up_hpc_for_testing(workflow, mocker)
    if write_job_script:
        mocked.side_effect = touch_job_script

    workflow._submit_hpc_job([("P1", "1")])
    assert expected_message in caplog.text


def test_submit_hpc_job_pysqa_error(
    workflow: PipelineWorkflow, mocker: pytest_mock.MockFixture
):
    def write_error_file(*args, **kwargs):
        fpath_error = workflow.dpath_pipeline_work / workflow.fname_hpc_error
        fpath_error.parent.mkdir(parents=True, exist_ok=True)
        fpath_error.write_text("PYSQA ERROR\n")

    mocked = _set_up_hpc_for_testing(workflow, mocker)
    mocked.side_effect = write_error_file
    with pytest.raises(
        RuntimeError, match="Error occurred while submitting the HPC job:\nPYSQA ERROR"
    ):
        workflow._submit_hpc_job([("P1", "1")])


@pytest.mark.parametrize("job_id", ["12345", None])
def test_submit_hpc_job_job_id(
    workflow: PipelineWorkflow,
    mocker: pytest_mock.MockFixture,
    caplog: pytest.LogCaptureFixture,
    job_id,
):
    mocked = _set_up_hpc_for_testing(workflow, mocker)
    mocked.return_value = job_id

    workflow._submit_hpc_job([("P1", "1")])
    if job_id is not None:
        assert f"HPC job ID: {job_id}" in caplog.text
    else:
        assert "HPC job ID" not in caplog.text


def test_run_main_hpc(mocker: pytest_mock.MockFixture, workflow: PipelineWorkflow):
    # Mock the _submit_hpc_job method
    mocker.patch("os.makedirs", mocker.MagicMock())
    mocked_submit_hpc_job = mocker.patch.object(workflow, "_submit_hpc_job")

    # Set the hpc attribute to "exists" to simulate that the HPC is available
    workflow.hpc = "exists"

    # Create test manifest and BIDS data
    participants_and_sessions = {"01": ["1", "2", "3"], "02": ["1"]}
    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions,
        participants_and_sessions_bidsified=participants_and_sessions,
        dpath_bidsified=workflow.layout.dpath_bids,
    )
    manifest.save_with_backup(workflow.layout.fpath_manifest)

    # Call the run_main method
    workflow.run_main()

    # Assert that the _submit_hpc_job method was called
    mocked_submit_hpc_job.assert_called_once()

    # Check "participants_sessions" positional argument
    assert list(mocked_submit_hpc_job.call_args[0][0]) == [
        ("01", "1"),
        ("01", "2"),
        ("01", "3"),
        ("02", "1"),
    ]


def test_generate_cli_command_for_hpc(workflow: PipelineWorkflow):
    with pytest.raises(
        NotImplementedError, match="This method should be implemented in a subclass"
    ):
        workflow._generate_cli_command_for_hpc()
