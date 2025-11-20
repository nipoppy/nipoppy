import pytest

from nipoppy.workflows.pipeline_store.search import PipelineSearchWorkflow
from nipoppy.zenodo_api import ZenodoAPI, ZenodoAPIError

MAX_ZENODO_SEARCH_SIZE = PipelineSearchWorkflow._api_search_size


@pytest.fixture
def zenodo_api() -> ZenodoAPI:
    return ZenodoAPI()


@pytest.mark.api
def test_search_size(zenodo_api: ZenodoAPI):
    zenodo_api.search_records("", size=MAX_ZENODO_SEARCH_SIZE)


@pytest.mark.api
def test_search_size_exceeds_max(zenodo_api: ZenodoAPI):
    with pytest.raises(
        ZenodoAPIError,
        match="Failed to search records. JSON response:",
    ):
        zenodo_api.search_records("", size=MAX_ZENODO_SEARCH_SIZE + 1)
