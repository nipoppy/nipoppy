"""Tests for PipelineListWorkflow."""

from pathlib import Path

import pytest
import pytest_mock

from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.env import CURRENT_SCHEMA_VERSION, PipelineTypeEnum
from nipoppy.workflows.pipeline_store.list import PipelineListWorkflow
from tests.conftest import create_empty_dataset


@pytest.fixture()
def workflow(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    workflow = PipelineListWorkflow(dpath_root)
    create_empty_dataset(dpath_root)
    return workflow


@pytest.mark.parametrize(
    "pipeline_config_dicts,expected_pipeline_info",
    [
        (
            [],
            {
                PipelineTypeEnum.BIDSIFICATION: {},
                PipelineTypeEnum.PROCESSING: {},
                PipelineTypeEnum.EXTRACTION: {},
            },
        ),
        (
            [
                {
                    "NAME": "pipeline1",
                    "VERSION": "0.0.1",
                    "PIPELINE_TYPE": PipelineTypeEnum.BIDSIFICATION,
                    "SCHEMA_VERSION": CURRENT_SCHEMA_VERSION,
                },
                {
                    "NAME": "pipeline1",
                    "VERSION": "0.0.2",
                    "PIPELINE_TYPE": PipelineTypeEnum.BIDSIFICATION,
                    "SCHEMA_VERSION": CURRENT_SCHEMA_VERSION,
                },
                {
                    "NAME": "pipeline2",
                    "VERSION": "0.1.0",
                    "PIPELINE_TYPE": PipelineTypeEnum.PROCESSING,
                    "SCHEMA_VERSION": CURRENT_SCHEMA_VERSION,
                },
                {
                    "NAME": "pipeline3",
                    "VERSION": "1.0.0",
                    "PIPELINE_TYPE": PipelineTypeEnum.EXTRACTION,
                    "SCHEMA_VERSION": CURRENT_SCHEMA_VERSION,
                },
            ],
            {
                PipelineTypeEnum.BIDSIFICATION: {"pipeline1": ["0.0.1", "0.0.2"]},
                PipelineTypeEnum.PROCESSING: {"pipeline2": ["0.1.0"]},
                PipelineTypeEnum.EXTRACTION: {"pipeline3": ["1.0.0"]},
            },
        ),
    ],
)
def test_get_pipeline_map_info(
    pipeline_config_dicts: list[dict],
    expected_pipeline_info: dict[str, list[str]],
    workflow: PipelineListWorkflow,
):
    for pipeline_config_dict in pipeline_config_dicts:
        pipeline_config = BasePipelineConfig(**pipeline_config_dict)
        fpath_config = (
            workflow.layout.get_dpath_pipeline_bundle(
                pipeline_config.PIPELINE_TYPE,
                pipeline_config.NAME,
                pipeline_config.VERSION,
            )
            / workflow.layout.fname_pipeline_config
        )
        fpath_config.parent.mkdir(parents=True, exist_ok=True)
        fpath_config.write_text(pipeline_config.model_dump_json())

    pipeline_info = workflow._get_pipeline_info_map()

    assert pipeline_info == expected_pipeline_info


def test_get_pipeline_info_map_error(workflow: PipelineListWorkflow):
    fpath_config = (
        workflow.layout.get_dpath_pipeline_bundle(
            PipelineTypeEnum.BIDSIFICATION, "pipeline1", "0.0.1"
        )
        / workflow.layout.fname_pipeline_config
    )
    fpath_config.parent.mkdir(parents=True, exist_ok=True)
    fpath_config.write_text("invalid json")

    with pytest.raises(RuntimeError, match="Error when loading pipeline config"):
        workflow._get_pipeline_info_map()


@pytest.mark.parametrize(
    "pipeline_info",
    [
        {"pipeline1": ["0.0.1", "0.0.2"], "pipeline2": ["0.1.0"]},
        {"pipeline1": ["0.0.1"]},
    ],
)
@pytest.mark.parametrize(
    "pipeline_type",
    [
        PipelineTypeEnum.BIDSIFICATION,
        PipelineTypeEnum.PROCESSING,
        PipelineTypeEnum.EXTRACTION,
    ],
)
def test_log_pipeline_info(
    pipeline_type: PipelineTypeEnum,
    pipeline_info: dict[str, list[str]],
    workflow: PipelineListWorkflow,
    caplog: pytest.LogCaptureFixture,
):
    workflow._log_pipeline_info(pipeline_type, pipeline_info)
    assert f"[green]Available {pipeline_type.value}" in caplog.records[0].message
    for (pipeline_name, versions), log_record in zip(
        pipeline_info.items(), caplog.records[1:]
    ):
        assert pipeline_name in log_record.message
        for version in versions:
            assert version in log_record.message


@pytest.mark.parametrize(
    "pipeline_type",
    [
        PipelineTypeEnum.BIDSIFICATION,
        PipelineTypeEnum.PROCESSING,
        PipelineTypeEnum.EXTRACTION,
    ],
)
def test_log_pipeline_info_empty(
    pipeline_type: PipelineTypeEnum,
    workflow: PipelineListWorkflow,
    caplog: pytest.LogCaptureFixture,
):
    pipeline_info = {}
    workflow._log_pipeline_info(pipeline_type, pipeline_info)

    assert len(caplog.records) == 1
    assert (
        f"[red]No available {pipeline_type.value} pipelines"
        in caplog.records[0].message
    )


def test_run_main(
    workflow: PipelineListWorkflow,
    mocker: pytest_mock.MockFixture,
    caplog: pytest.LogCaptureFixture,
):
    pipeline_info_map = {
        PipelineTypeEnum.BIDSIFICATION: {
            "pipeline1": ["0.0.1", "0.0.2"],
            "pipeline2": ["0.1.0"],
        },
        PipelineTypeEnum.PROCESSING: {},
        PipelineTypeEnum.EXTRACTION: {},
    }
    mocked_get_pipeline_info_map = mocker.patch.object(
        workflow, "_get_pipeline_info_map", return_value=pipeline_info_map
    )
    mocked_log_pipeline_info = mocker.patch.object(workflow, "_log_pipeline_info")

    workflow.run_main()

    assert (
        caplog.records[0].message
        == f"Checking pipelines installed in {workflow.layout.dpath_pipelines}"
    )
    assert "Pipelines can be installed with the " in caplog.records[-1].message

    mocked_get_pipeline_info_map.assert_called_once()
    mocked_log_pipeline_info.assert_has_calls(
        [
            mocker.call(
                PipelineTypeEnum.BIDSIFICATION,
                pipeline_info_map[PipelineTypeEnum.BIDSIFICATION],
            ),
            mocker.call(
                PipelineTypeEnum.PROCESSING,
                pipeline_info_map[PipelineTypeEnum.PROCESSING],
            ),
            mocker.call(
                PipelineTypeEnum.EXTRACTION,
                pipeline_info_map[PipelineTypeEnum.EXTRACTION],
            ),
        ],
    )
