"""Tests for PipelineListWorkflow."""

from pathlib import Path

import pytest
import pytest_mock

from nipoppy.env import PipelineTypeEnum
from nipoppy.logger import LogColor
from nipoppy.workflows.pipeline_store.list import PipelineListWorkflow
from tests.conftest import create_empty_dataset


@pytest.fixture()
def workflow(tmp_path: Path):
    dpath_root = tmp_path / "my_dataset"
    workflow = PipelineListWorkflow(dpath_root)
    create_empty_dataset(dpath_root)
    return workflow


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
@pytest.mark.no_xdist
def test_log_pipeline_info(
    pipeline_type: PipelineTypeEnum,
    pipeline_info: dict[str, list[str]],
    workflow: PipelineListWorkflow,
    caplog: pytest.LogCaptureFixture,
):
    workflow._log_pipeline_info(pipeline_type, pipeline_info)
    assert (
        f"[bold {LogColor.EMPHASIZE}]Available {pipeline_type.value}"
        in caplog.records[0].message
    )
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
@pytest.mark.no_xdist
def test_log_pipeline_info_empty(
    pipeline_type: PipelineTypeEnum,
    workflow: PipelineListWorkflow,
    caplog: pytest.LogCaptureFixture,
):
    pipeline_info = {}
    workflow._log_pipeline_info(pipeline_type, pipeline_info)

    assert len(caplog.records) == 1
    assert f"No available {pipeline_type.value} pipelines" in caplog.records[0].message


@pytest.mark.no_xdist
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
        workflow.study, "_get_pipeline_info_map", return_value=pipeline_info_map
    )
    mocked_log_pipeline_info = mocker.patch.object(workflow, "_log_pipeline_info")

    workflow.run_main()

    assert (
        caplog.records[0].message
        == f"Checking pipelines installed in {workflow.study.layout.dpath_pipelines}"
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
