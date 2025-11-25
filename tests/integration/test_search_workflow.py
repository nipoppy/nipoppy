import pytest

from nipoppy.workflows.pipeline_store.search import PipelineSearchWorkflow
from nipoppy.zenodo_api import ZenodoAPI, ZenodoAPIError


@pytest.fixture
def zenodo_api() -> ZenodoAPI:
    return ZenodoAPI()


@pytest.mark.api
def test_search_size(zenodo_api: ZenodoAPI):
    PipelineSearchWorkflow(
        query="",
        zenodo_api=zenodo_api,
    ).run()


@pytest.mark.api
def test_search_size_exceeds_max(zenodo_api: ZenodoAPI):
    workflow = PipelineSearchWorkflow(
        query="",
        zenodo_api=zenodo_api,
    )
    workflow._api_search_size += 1
    with pytest.raises(
        ZenodoAPIError,
        match="Failed to search records. JSON response:",
    ):
        workflow.run()
