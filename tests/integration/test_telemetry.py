import pytest

from nipoppy.workflows.services.telemetry import _get_user_country


@pytest.mark.api
def test_get_user_country():
    assert len(_get_user_country()) == 2
