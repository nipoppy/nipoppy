"""Tests for BasePipelineWorkflow."""

import json
import logging
from pathlib import Path
from typing import Optional

import pytest
from fids import fids

from nipoppy.config.boutiques import BoutiquesConfig
from nipoppy.config.container import ContainerInfo
from nipoppy.config.pipeline import PipelineConfig
from nipoppy.config.pipeline_step import PipelineStepConfig
from nipoppy.utils import StrOrPathLike, strip_session
from nipoppy.workflows.pipeline import BasePipelineWorkflow

from .conftest import datetime_fixture  # noqa F401
from .conftest import create_empty_dataset, get_config, prepare_dataset


class PipelineWorkflow(BasePipelineWorkflow):
    def __init__(
        self,
        dpath_root: StrOrPathLike,
        pipeline_name: str,
        pipeline_version: str,
        pipeline_step: Optional[str] = None,
        participant: str = None,
        session: str = None,
        fpath_layout: Optional[StrOrPathLike] = None,
        logger: Optional[logging.Logger] = None,
        dry_run: bool = False,
    ):
        self._n_runs = 0
        self._n_errors = 0
        super().__init__(
            dpath_root=dpath_root,
            name="test",
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            pipeline_step=pipeline_step,
            participant=participant,
            session=session,
            fpath_layout=fpath_layout,
            logger=logger,
            dry_run=dry_run,
        )

        # override the config
        self.config = get_config(
            visits=["1"],
            bids_pipelines=[
                # built-in pipelines
                {
                    "NAME": "heudiconv",
                    "VERSION": "0.12.2",
                    "CONTAINER_INFO": {"PATH": "heudiconv.sif"},
                    "STEPS": [{"NAME": "prepare"}, {"NAME": "convert"}],
                }
            ],
            proc_pipelines=[
                # built-in pipelines
                {
                    "NAME": "fmriprep",
                    "VERSION": "23.1.3",
                    "CONTAINER_INFO": {"PATH": "fmriprep.sif"},
                    "STEPS": [{}],
                },
                # user-added pipeline
                {
                    "NAME": "my_pipeline",
                    "VERSION": "1.0",
                    "CONTAINER_INFO": {"PATH": "my_container.sif"},
                    "STEPS": [{}],
                },
            ],
        )

    def run_single(self, subject: str, session: str):
        """Run on a single subject/session."""
        self._n_runs += 1
        self.logger.info(f"Running on {subject}/{session}")
        if subject == "FAIL":
            self._n_errors += 1
            raise RuntimeError("FAIL")


@pytest.fixture
def workflow(tmp_path: Path):
    return PipelineWorkflow(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
    )


def _make_dummy_json(fpath: StrOrPathLike):
    fpath: Path = Path(fpath)
    fpath.parent.mkdir(parents=True, exist_ok=True)
    fpath.write_text("{}\n")


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
    assert hasattr(workflow, "participant")
    assert hasattr(workflow, "session")
    assert isinstance(workflow.dpath_pipeline, Path)
    assert isinstance(workflow.dpath_pipeline_output, Path)
    assert isinstance(workflow.dpath_pipeline_work, Path)
    assert isinstance(workflow.dpath_pipeline_bids_db, Path)


def test_pipeline_config(workflow: PipelineWorkflow):
    assert isinstance(workflow.pipeline_config, PipelineConfig)


def test_fpath_container(tmp_path: Path):
    workflow = PipelineWorkflow(
        dpath_root=(tmp_path / "my_dataset"),
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
    )
    workflow.layout.dpath_containers.mkdir(parents=True, exist_ok=True)
    (workflow.layout.dpath_containers / "my_container.sif").touch()
    assert isinstance(workflow.fpath_container, Path)


def test_fpath_container_not_found(workflow: PipelineWorkflow):
    with pytest.raises(FileNotFoundError, match="No container image file found at"):
        workflow.fpath_container


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,pipeline_step",
    [
        ("fmriprep", "23.1.3", None),  # built-in pipeline
        ("heudiconv", "0.12.2", "prepare"),  # built-in pipeline
        ("custom_pipeline", "1.0", None),
    ],
)
def test_descriptor(pipeline_name, pipeline_version, pipeline_step, tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    workflow = PipelineWorkflow(
        dpath_root, pipeline_name, pipeline_version, pipeline_step
    )

    # user-added pipelines with descriptor file
    fpath_descriptor_custom = tmp_path / "custom_pipeline.json"
    workflow.config.PROC_PIPELINES.extend(
        [
            PipelineConfig(
                NAME="custom_pipeline",
                VERSION="1.0",
                CONTAINER_INFO=ContainerInfo(PATH="my_container.sif"),
                STEPS=[PipelineStepConfig(DESCRIPTOR_FILE=fpath_descriptor_custom)],
            ),
        ]
    )
    _make_dummy_json(fpath_descriptor_custom)
    assert isinstance(workflow.descriptor, dict)


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,invocation",
    [
        ("my_pipeline", "1.0", {"key1": "val1", "key2": "val2"}),
        ("fmriprep", "23.1.3", {}),
    ],
)
def test_invocation(pipeline_name, pipeline_version, invocation, tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    workflow = PipelineWorkflow(dpath_root, pipeline_name, pipeline_version)

    fpath_invocation = tmp_path / "invocation.json"
    fpath_invocation.write_text(json.dumps(invocation))

    workflow.pipeline_config.get_step_config().INVOCATION_FILE = fpath_invocation
    assert workflow.invocation == invocation


def test_invocation_none(workflow: PipelineWorkflow):
    with pytest.raises(ValueError, match="No invocation file specified in config"):
        workflow.invocation


@pytest.mark.parametrize("return_str", [True, False])
def test_process_template_json(return_str, tmp_path: Path):
    workflow = PipelineWorkflow(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
    )

    class Test:
        extra2 = "extra_obj_attribute"

    processed = workflow.process_template_json(
        {
            "[[NIPOPPY_BIDS_ID]]": "[[NIPOPPY_PARTICIPANT]]",
            "[[NIPOPPY_SESSION]]": "[[NIPOPPY_SESSION_SHORT]]",
            "[[NIPOPPY_DPATH_PIPELINE]]": "[[NIPOPPY_DPATH_BIDS]]",
            "[[NIPOPPY_EXTRA1]]": "[[NIPOPPY_EXTRA2]]",
        },
        participant="01",
        session="ses-1",
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
        "[[NIPOPPY_BIDS_ID]]",
        "[[NIPOPPY_PARTICIPANT]]",
        "[[NIPOPPY_SESSION]]",
        "[[NIPOPPY_SESSION_SHORT]]",
        "[[NIPOPPY_DPATH_PIPELINE]]",
        "[[NIPOPPY_DPATH_BIDS]]",
        "[[NIPOPPY_EXTRA1]]",
        "[[NIPOPPY_EXTRA2]]",
    ]:
        assert pattern not in processed


@pytest.mark.parametrize("participant,session", [("123", None), (None, "ses-1")])
def test_process_template_json_error(participant, session, tmp_path: Path):
    workflow = PipelineWorkflow(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
    )

    with pytest.raises(ValueError, match="participant and session must be strings"):
        workflow.process_template_json(
            {},
            participant=participant,
            session=session,
        )


def test_get_boutiques_config(tmp_path: Path):
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

    boutiques_config = workflow.get_boutiques_config()
    assert isinstance(boutiques_config, BoutiquesConfig)
    # should not be the default
    assert boutiques_config != BoutiquesConfig()


def test_get_boutiques_config_default(tmp_path: Path):
    workflow = PipelineWorkflow(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="no_boutiques_config",
        pipeline_version="1.0",
    )
    workflow.descriptor = {}
    boutiques_config = workflow.get_boutiques_config()
    assert isinstance(boutiques_config, BoutiquesConfig)
    # expect the default
    assert boutiques_config == BoutiquesConfig()


def test_get_boutiques_config_invalid(tmp_path: Path):
    workflow = PipelineWorkflow(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="bad_boutiques_config",
        pipeline_version="1.0",
    )
    workflow.descriptor = {"custom": {"nipoppy": {"INVALID_ARG": "value"}}}

    with pytest.raises(ValueError, match="Error when loading the Boutiques config"):
        workflow.get_boutiques_config()


@pytest.mark.parametrize(
    "participant,session,expected_count",
    [
        (None, None, 12),
        ("01", None, 6),
        ("02", None, 6),
        (None, "ses-1", 5),
        (None, "ses-2", 5),
        (None, "ses-3", 2),
        ("01", "ses-3", 2),
        ("02", "ses-3", 0),
    ],
)
def test_set_up_bids_db(participant, session, expected_count, tmp_path: Path):
    workflow = PipelineWorkflow(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
    )
    dpath_bids_db = tmp_path / "bids_db"
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
        dpath_bids_db=dpath_bids_db,
        participant=participant,
        session=strip_session(session),
    )
    assert dpath_bids_db.exists()
    assert len(bids_layout.get(extension=".nii.gz")) == expected_count


@pytest.mark.parametrize("dry_run", [True, False])
def test_run_setup(dry_run: bool, tmp_path: Path):
    workflow = PipelineWorkflow(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
        dry_run=dry_run,
    )
    create_empty_dataset(workflow.layout.dpath_root)
    workflow.run_setup()
    assert workflow.dpath_pipeline.exists() == (not dry_run)

    # run again, should not fail even if directories already exist
    workflow.run_setup()


@pytest.mark.parametrize(
    "participant,session,expected_count",
    [(None, None, 4), ("01", None, 3), ("01", "ses-2", 1)],
)
def test_run_main(participant, session, expected_count, tmp_path: Path):
    workflow = PipelineWorkflow(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
        participant=participant,
        session=session,
    )

    participants_and_sessions = {"01": ["ses-1", "ses-2", "ses-3"], "02": ["ses-1"]}
    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions,
        participants_and_sessions_bidsified=participants_and_sessions,
        dpath_bidsified=workflow.layout.dpath_bids,
    )
    manifest.save_with_backup(workflow.layout.fpath_manifest)
    workflow.run_main()
    assert workflow._n_runs == expected_count


def test_run_main_catch_errors(tmp_path: Path):
    workflow = PipelineWorkflow(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
        participant="FAIL",
        session="1",
    )

    participants_and_sessions = {"FAIL": ["ses-1"]}
    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions,
        participants_and_sessions_bidsified=participants_and_sessions,
        dpath_bidsified=workflow.layout.dpath_bids,
    )
    manifest.save_with_backup(workflow.layout.fpath_manifest)
    workflow.run_main()
    assert workflow._n_runs == 1
    assert workflow._n_errors == 1


@pytest.mark.parametrize(
    "participant,session,expected_count",
    [(None, None, 4), ("01", None, 3), ("02", None, 1), ("01", "ses-2", 1)],
)
def test_get_participants_sessions_to_run(
    participant, session, expected_count, tmp_path: Path
):
    workflow = PipelineWorkflow(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name="my_pipeline",
        pipeline_version="1.0",
        participant=participant,
        session=session,
    )

    participants_and_sessions_manifest = {
        "01": ["ses-1", "ses-2", "ses-3"],
        "02": ["ses-1", "ses-2", "ses-3"],
    }
    participants_and_sessions_bidsified = {
        "01": ["ses-1", "ses-2", "ses-3"],
        "02": ["ses-1"],
    }
    manifest = prepare_dataset(
        participants_and_sessions_manifest=participants_and_sessions_manifest,
        participants_and_sessions_bidsified=participants_and_sessions_bidsified,
        dpath_bidsified=workflow.layout.dpath_bids,
    )
    manifest.save_with_backup(workflow.layout.fpath_manifest)
    workflow.run_main()
    assert workflow._n_runs == expected_count


@pytest.mark.parametrize(
    "pipeline_name,pipeline_version,participant,session,expected_stem",
    [
        ("pipeline1", "v1", "sub1", None, "test/pipeline1-v1/pipeline1-v1-sub1"),
        ("pipeline2", "2.0", None, "ses-1", "test/pipeline2-2.0/pipeline2-2.0-1"),
    ],
)
def test_generate_fpath_log(
    pipeline_name,
    pipeline_version,
    participant,
    session,
    expected_stem,
    tmp_path: Path,
    datetime_fixture,  # noqa F811
):
    workflow = PipelineWorkflow(
        dpath_root=tmp_path / "my_dataset",
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        participant=participant,
        session=session,
    )
    fpath_log = workflow.generate_fpath_log()
    assert (
        fpath_log == workflow.layout.dpath_logs / f"{expected_stem}-20240404_1234.log"
    )
