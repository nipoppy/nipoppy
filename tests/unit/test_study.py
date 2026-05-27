"""Tests for the Study class."""

import pytest
import pytest_mock

from nipoppy.config.pipeline import BasePipelineConfig
from nipoppy.env import PipelineTypeEnum
from nipoppy.exceptions import ConfigError
from nipoppy.study import Study
from tests.conftest import CURRENT_SCHEMA_VERSION, get_config


def test_len(study: Study, mocker: pytest_mock.MockFixture):
    study.manifest = mocker.MagicMock()
    study.manifest.__len__.return_value = 5
    assert len(study) == 5


def test_config(study: Study, mocker: pytest_mock.MockFixture):
    config = get_config(dicom_dir_map_file="[[NIPOPPY_DPATH_ROOT]]")
    mocked_load = mocker.patch("nipoppy.study.Config.load", return_value=config)

    processed_config = study.config

    # test load
    mocked_load.assert_called_once_with(study.layout.fpath_config)

    # test placeholder replacement
    assert str(processed_config.DICOM_DIR_MAP_FILE) == str(study.layout.dpath_root)


@pytest.mark.parametrize(
    "property_name,layout_attribute_name,tabular_class",
    [
        ("manifest", "fpath_manifest", "Manifest"),
        ("curation_status_table", "fpath_curation_status", "CurationStatusTable"),
        ("processing_status_table", "fpath_processing_status", "ProcessingStatusTable"),
    ],
)
def test_tabular_file_load(
    property_name,
    layout_attribute_name,
    tabular_class: str,
    study: Study,
    mocker: pytest_mock.MockFixture,
):
    fpath = study.layout.dpath_root / "tabular_file.tsv"
    mocker.patch.object(study.layout, layout_attribute_name, new=fpath)
    mocked_load = mocker.patch(f"nipoppy.study.{tabular_class}.load")

    # access the property
    getattr(study, property_name)

    mocked_load.assert_called_once_with(fpath)


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
    study: Study,
    pipeline_config_dicts: list[dict],
    expected_pipeline_info: dict[str, list[str]],
):
    for pipeline_config_dict in pipeline_config_dicts:
        pipeline_config = BasePipelineConfig(**pipeline_config_dict)
        fpath_config = (
            study.layout.get_dpath_pipeline_bundle(
                pipeline_config.PIPELINE_TYPE,
                pipeline_config.NAME,
                pipeline_config.VERSION,
            )
            / study.layout.fname_pipeline_config
        )
        fpath_config.parent.mkdir(parents=True, exist_ok=True)
        fpath_config.write_text(pipeline_config.model_dump_json())

    pipeline_info = study._get_pipeline_info_map()

    assert pipeline_info == expected_pipeline_info


def test_get_pipeline_info_map_error(study: Study):
    fpath_config = (
        study.layout.get_dpath_pipeline_bundle(
            PipelineTypeEnum.BIDSIFICATION, "pipeline1", "0.0.1"
        )
        / study.layout.fname_pipeline_config
    )
    fpath_config.parent.mkdir(parents=True, exist_ok=True)
    fpath_config.write_text("invalid json")

    with pytest.raises(ConfigError, match="Error when loading pipeline config"):
        study._get_pipeline_info_map()


@pytest.mark.parametrize(
    "pipeline_type,expected_output",
    [
        (
            "bidsification",
            {"pipeline1": ["0.0.1", "0.0.2"]},
        ),
        (
            "processing",
            {"pipeline2": ["0.1.0"]},
        ),
        (
            "extraction",
            {"pipeline3": ["1.0.0"], "pipeline4": ["2.0.0"]},
        ),
    ],
)
def test_get_installed_pipelines(
    study: Study,
    pipeline_type: str,
    expected_output: dict,
    mocker: pytest_mock.MockFixture,
):
    pipeline_info_map = {
        PipelineTypeEnum.BIDSIFICATION: {"pipeline1": ["0.0.1", "0.0.2"]},
        PipelineTypeEnum.PROCESSING: {"pipeline2": ["0.1.0"]},
        PipelineTypeEnum.EXTRACTION: {"pipeline3": ["1.0.0"], "pipeline4": ["2.0.0"]},
    }
    mocker.patch.object(study, "_get_pipeline_info_map", return_value=pipeline_info_map)

    installed_pipelines = study.get_installed_pipelines(pipeline_type)

    assert installed_pipelines == expected_output


def test_get_installed_pipelines_invalid_type(study: Study):
    with pytest.raises(ValueError, match="Invalid pipeline type"):
        study.get_installed_pipelines("invalid_type")
