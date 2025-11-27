import pytest

from nipoppy.exceptions import ConfigError
from nipoppy.workflows.pipeline_store.search import PipelineSearchWorkflow
from nipoppy.zenodo_api import ZenodoAPI


@pytest.fixture
def zenodo_api() -> ZenodoAPI:
    return ZenodoAPI()


@pytest.mark.api
def test_search_size(zenodo_api, mocker):
    spy = mocker.spy(zenodo_api, "search_records")
    sizes = [1, 5, 10]
    for s in sizes:
        PipelineSearchWorkflow(query="", zenodo_api=zenodo_api, size=s).run()
        spy.assert_called_with(
            query="", community_id=None, keywords=["Nipoppy"], size=s
        )


@pytest.mark.api
def test_search_size_exceeds_max(zenodo_api: ZenodoAPI):
    workflow = PipelineSearchWorkflow(
        query="",
        zenodo_api=zenodo_api,
        size=PipelineSearchWorkflow._api_search_size + 1,
    )
    with pytest.raises(
        ConfigError,
        match=(
            r"Provided search size \(\d+\) is larger than allowed by api"
            f" \\({PipelineSearchWorkflow._api_search_size}\\)"
        ),
    ):
        workflow.run()
