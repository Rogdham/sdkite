import sys

from requests import Response, Session
from urllib3.util import SKIP_HEADER  # type: ignore[attr-defined]

from sdkite.http.model import HTTPHeaderDict, HTTPRequest, HTTPResponse

if sys.version_info < (3, 8):  # pragma: no cover
    from backports.cached_property import cached_property
else:  # pragma: no cover
    from functools import cached_property

if sys.version_info < (3, 9):  # pragma: no cover
    from typing import Iterator
else:  # pragma: no cover
    from collections.abc import Iterator


class RequestsResponse(HTTPResponse):
    def __init__(self, response: Response):
        self._response = response

    @property
    def raw(self) -> Response:
        return self._response

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def reason(self) -> str:
        return self._response.reason

    @cached_property
    def headers(self) -> HTTPHeaderDict:
        return HTTPHeaderDict(self._response.raw.headers)

    @cached_property
    def data_stream(self) -> Iterator[bytes]:
        return self._response.iter_content()

    @property
    def data_bytes(self) -> bytes:
        return self._response.content

    @property
    def data_str(self) -> str:
        return self._response.text

    @cached_property
    def data_json(self) -> object:
        return self._response.json()


class RequestsImpl:
    def __init__(self) -> None:
        self.session = Session()

    def __call__(self, request: HTTPRequest) -> HTTPResponse:
        headers = request.headers

        # remove request/urllib3 User-Agent header
        if "user-agent" not in headers:
            headers = HTTPHeaderDict(headers)  # copy
            headers["user-agent"] = SKIP_HEADER

        response = self.session.request(
            method=request.method,
            url=request.url,
            headers=headers,
            data=request.body,
            stream=request.stream_response,
            allow_redirects=False,
        )

        return RequestsResponse(response)
