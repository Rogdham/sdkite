import pytest
from requests_mock import Mocker


@pytest.fixture(autouse=True)
def _mock_requests(
    requests_mock: Mocker,  # pylint: disable=unused-argument # noqa: ARG001
) -> None:
    pass
