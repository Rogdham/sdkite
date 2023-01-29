import sys

import pytest
from requests_mock import Mocker

if sys.version_info < (3, 9):  # pragma: no cover
    from typing import Iterator
else:  # pragma: no cover
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def mock_requests(
    requests_mock: Mocker,  # pylint: disable=unused-argument
) -> Iterator[None]:
    yield
