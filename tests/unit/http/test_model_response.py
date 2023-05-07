import sys

import pytest

from sdkite.http import HTTPContextError, HTTPHeaderDict, HTTPRequest, HTTPResponse

if sys.version_info < (3, 9):  # pragma: no cover
    from typing import Iterator
else:  # pragma: no cover
    from collections.abc import Iterator


class FakeResponse(HTTPResponse):
    def __init__(self) -> None:
        self.is_closed = False

    @property
    def raw(self) -> object:
        raise NotImplementedError

    @property
    def status_code(self) -> int:
        raise NotImplementedError

    @property
    def reason(self) -> str:
        raise NotImplementedError

    @property
    def headers(self) -> HTTPHeaderDict:
        raise NotImplementedError

    @property
    def data_stream(self) -> Iterator[bytes]:
        raise NotImplementedError

    @property
    def data_bytes(self) -> bytes:
        raise NotImplementedError

    @property
    def data_str(self) -> str:
        raise NotImplementedError

    @property
    def data_json(self) -> object:
        raise NotImplementedError

    def _close(self) -> None:
        self.is_closed = True


@pytest.mark.parametrize("raise_exception", [False, True])
def test_response_context_manager(raise_exception: bool) -> None:
    request = HTTPRequest(
        method="GET",
        url="https://example.com/",
        headers=HTTPHeaderDict(),
        body=b"",
        stream_response=False,
    )
    response = FakeResponse()
    response._set_context(request)  # pylint: disable=protected-access

    if raise_exception:
        with pytest.raises(HTTPContextError) as excinfo:  # noqa: SIM117, PT012
            with response:
                assert not response.is_closed
                raise ValueError("oops")

        exception = excinfo.value
        assert str(exception) == "ValueError: oops"
        assert exception.request == request
        assert exception.response == response
        assert isinstance(exception.__context__, ValueError)

    else:
        with response:
            assert not response.is_closed

    assert response.is_closed
