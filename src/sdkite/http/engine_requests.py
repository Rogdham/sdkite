import sys

import requests
import urllib3

from sdkite.http.exceptions import HTTPConnectionError, HTTPError, HTTPTimeoutError
from sdkite.http.model import HTTPHeaderDict, HTTPRequest, HTTPResponse
from sdkite.utils import walk_exception_context

if sys.version_info < (3, 8):  # pragma: no cover
    from backports.cached_property import cached_property
else:  # pragma: no cover
    from functools import cached_property

if sys.version_info < (3, 9):  # pragma: no cover
    from typing import Iterator
else:  # pragma: no cover
    from collections.abc import Iterator


class HTTPResponseRequests(HTTPResponse):
    def __init__(self, response: requests.Response) -> None:
        self._response = response

    @property
    def raw(self) -> requests.Response:
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

    def _close(self) -> None:
        self._response.close()


def _extract_exception(exception: BaseException) -> BaseException:
    wanted_exception = walk_exception_context(
        exception, (requests.RequestException, urllib3.exceptions.HTTPError)
    )
    return exception if wanted_exception is None else wanted_exception


class HTTPEngineRequests:
    def __init__(self) -> None:
        self.session = requests.Session()

    def __call__(self, request: HTTPRequest) -> HTTPResponse:
        headers = request.headers

        # remove request/urllib3 User-Agent header
        if "user-agent" not in headers:
            headers = HTTPHeaderDict(headers)  # copy
            headers["user-agent"] = urllib3.util.SKIP_HEADER  # type: ignore[attr-defined]

        try:
            response = self.session.request(
                method=request.method,
                url=request.url,
                headers=headers,
                data=request.body,
                stream=request.stream_response,
                allow_redirects=False,
                timeout=(40, 600 if request.stream_response else 30),
            )
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ProxyError,
        ) as ex:  # pragma: no cover
            raise HTTPConnectionError.from_exception(
                _extract_exception(ex), request=request
            ) from ex
        except requests.exceptions.Timeout as ex:  # pragma: no cover
            raise HTTPTimeoutError.from_exception(
                _extract_exception(ex), request=request
            ) from ex
        except Exception as ex:  # pragma: no cover  # noqa: BLE001
            raise HTTPError.from_exception(
                _extract_exception(ex), request=request
            ) from ex

        return HTTPResponseRequests(response)
