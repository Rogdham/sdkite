import sys

import pytest

from sdkite.http import HTTPContextError, HTTPHeaderDict, HTTPRequest, HTTPResponse

if sys.version_info < (3, 9):  # pragma: no cover
    from typing import Iterator
else:  # pragma: no cover
    from collections.abc import Iterator


class FakeResponse(HTTPResponse):
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


def test_response_context_manager() -> None:
    request = HTTPRequest(
        method="GET",
        url="https://example.com/",
        headers=HTTPHeaderDict(),
        body=b"",
        stream_response=False,
    )
    response = FakeResponse()
    response._set_context(request)  # pylint: disable=protected-access

    with response:
        pass

    with pytest.raises(HTTPContextError) as excinfo:  # noqa: SIM117, PT012
        with response:
            raise ValueError("oops")

    exception = excinfo.value
    assert str(exception) == "ValueError: oops"
    assert exception.request == request
    assert exception.response == response
    assert isinstance(exception.__context__, ValueError)
