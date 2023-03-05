import re
import sys
from typing import Any, Dict, List, Optional, Tuple, Union
from unittest.mock import Mock, call

import pytest

from sdkite.http import (
    HTTPAdapter,
    HTTPBodyEncoding,
    HTTPContextError,
    HTTPHeaderDict,
    HTTPRequest,
    HTTPRequestAttemptInfo,
    HTTPResponse,
    HTTPStatusCodeError,
)

if sys.version_info < (3, 9):  # pragma: no cover
    from typing import Iterator
else:  # pragma: no cover
    from collections.abc import Iterator


class FakeResponse(HTTPResponse):
    def __init__(self, status_code: int = 200) -> None:
        self._status_code = status_code

    @property
    def raw(self) -> object:
        raise NotImplementedError

    @property
    def status_code(self) -> int:
        return self._status_code

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


def create_adapter(
    url: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    parent_adapter: Optional[HTTPAdapter] = None,
) -> Tuple[HTTPAdapter, Mock, Mock]:
    # pylint: disable=protected-access
    send_request = Mock()
    send_request.return_value.status_code = 200
    adapter = HTTPAdapter(send_request)
    adapter._attr_name = "http"
    client = Mock()
    client.http = adapter
    adapter._clients = (client,)
    if parent_adapter:
        adapter._clients = parent_adapter._clients + adapter._clients
    adapter.url = url
    adapter.headers = HTTPHeaderDict(headers)
    adapter.retry_nb_attempts = None
    adapter.retry_callback = None
    adapter.retry_wait_initial = 0  # change default value for faster tests
    adapter.retry_wait_max = None
    adapter.retry_wait_jitter = 0  # change default value for faster tests
    adapter.request_interceptor = {}
    adapter.response_interceptor = {}
    return (adapter, send_request, client)


@pytest.mark.parametrize("method", ["post", "pOsT", "POST"])
def test_request_method(method: str) -> None:
    adapter, send_request, _ = create_adapter()
    response = adapter.request(method, "https://www.example.com")
    assert response == send_request.return_value
    assert send_request.call_args_list == [
        call(
            HTTPRequest(
                method="POST",
                url="https://www.example.com",
                headers=HTTPHeaderDict(),
                body=b"",
                stream_response=False,
            )
        )
    ]


@pytest.mark.parametrize(
    ["base_url", "url"],
    [
        (None, "https://www.example.com/foo/bar"),
        ("https://www.example.com", "foo/bar"),
        ("https://www.example.com/", "foo/bar"),
        ("https://www.example.com/foo", "bar"),
        ("https://www.example.com/foo/", "bar"),
        ("https://www.example.com/foo/bar", ""),
        ("https://www.example.com/foo/bar", None),
        ("https://www.example.com", "/foo/bar"),
        ("https://www.example.com/", "/foo/bar"),
        ("https://www.example.com/abc/def", "/foo/bar"),
        ("https://www.example.com/foo/abc/def", "../../bar"),
    ],
)
def test_request_url(base_url: Optional[str], url: Optional[str]) -> None:
    adapter, send_request, _ = create_adapter(base_url)
    response = adapter.request("GET", url)
    assert response == send_request.return_value
    assert send_request.call_args_list == [
        call(
            HTTPRequest(
                method="GET",
                url="https://www.example.com/foo/bar",
                headers=HTTPHeaderDict(),
                body=b"",
                stream_response=False,
            )
        )
    ]


def test_request_retry_status_code() -> None:
    adapter, send_request, _ = create_adapter()

    request_attempt = 0

    def do_send_request(_: HTTPRequest) -> FakeResponse:
        nonlocal request_attempt
        request_attempt += 1
        return FakeResponse(200 if request_attempt == 3 else 503)

    send_request.side_effect = do_send_request

    # fail with only 2 attempts
    with pytest.raises(HTTPStatusCodeError):
        adapter.request("GET", "https://www.example.com", retry_nb_attempts=2)

    # works with more attempts
    request_attempt = 0
    adapter.request("GET", "https://www.example.com")


@pytest.mark.parametrize(
    ["success_at_attempt_nb", "retry_nb_attempts_arg", "expected_error_at_attempt"],
    [
        # default retry_nb_attempts
        pytest.param(1, None, None, id="default-1"),
        pytest.param(2, None, None, id="default-2"),
        pytest.param(3, None, None, id="default-3"),
        pytest.param(4, None, 3, id="default-4"),
        pytest.param(5, None, 3, id="default-5"),
        # custom retry_nb_attempts argument
        pytest.param(1, 2, None, id="custom-1"),
        pytest.param(2, 2, None, id="custom-2"),
        pytest.param(3, 2, 2, id="custom-3"),
        pytest.param(4, 2, 2, id="custom-4"),
        pytest.param(5, 2, 2, id="custom-5"),
    ],
)
def test_request_retry(
    success_at_attempt_nb: int,
    retry_nb_attempts_arg: Optional[int],
    expected_error_at_attempt: Optional[bool],
) -> None:
    adapter, send_request, client = create_adapter()

    adapter.request_interceptor["inter"] = 0

    # side-effect on request in interceptor to test initial_request in retry callback
    def intercept(request: HTTPRequest, _: HTTPAdapter) -> HTTPRequest:
        request.headers["X-Intercepted"] = "yes"
        return request

    client.inter.side_effect = intercept

    expected_response = FakeResponse()

    class CustomError(Exception):
        def __eq__(self, other: Any) -> bool:
            return type(self) is type(other) and self.args == other.args

    request_attempt = 0

    def do_send_request(_: HTTPRequest) -> FakeResponse:
        nonlocal request_attempt
        request_attempt += 1
        if request_attempt == success_at_attempt_nb:
            return expected_response
        raise CustomError(f"Send request error {request_attempt}")

    send_request.side_effect = do_send_request

    logged_retries: List[Tuple[int, BaseException]] = []

    def retry_callback(attempt_info: HTTPRequestAttemptInfo) -> None:
        logged_retries.append((attempt_info.attempt_number, attempt_info.exception))
        assert attempt_info.initial_request == HTTPRequest(
            "GET", "https://www.example.com", HTTPHeaderDict(), b"", False
        )
        assert 0.0 < attempt_info.seconds_since_start < 0.1

    kwargs: Any = {
        "retry_callback": retry_callback,
    }
    if retry_nb_attempts_arg is not None:
        kwargs["retry_nb_attempts"] = retry_nb_attempts_arg

    if expected_error_at_attempt is None:
        response = adapter.request("GET", "https://www.example.com", **kwargs)
        assert response == expected_response

    else:
        with pytest.raises(
            CustomError,
            match=re.escape(f"Send request error {expected_error_at_attempt}"),
        ):
            adapter.request("GET", "https://www.example.com", **kwargs)

    assert logged_retries == [
        (i, CustomError(f"Send request error {i}"))
        for i in range(1, min(success_at_attempt_nb, retry_nb_attempts_arg or 3))
    ], "retry_callback"


def test_no_request_url() -> None:
    adapter, _, _ = create_adapter()
    with pytest.raises(ValueError, match=re.escape("No URL provided")):
        adapter.request("GET")


def test_request_body_raw() -> None:
    adapter, send_request, _ = create_adapter()
    response = adapter.request("POST", "https://www.example.com", body=b"foobar")
    assert response == send_request.return_value
    assert send_request.call_args_list == [
        call(
            HTTPRequest(
                method="POST",
                url="https://www.example.com",
                headers=HTTPHeaderDict(),
                body=b"foobar",
                stream_response=False,
            )
        )
    ]


def test_request_body_json() -> None:
    adapter, send_request, _ = create_adapter()
    response = adapter.request(
        "POST",
        "https://www.example.com",
        body="foobar",
        body_encoding=HTTPBodyEncoding.JSON,
    )
    assert response == send_request.return_value
    assert send_request.call_args_list == [
        call(
            HTTPRequest(
                method="POST",
                url="https://www.example.com",
                headers=HTTPHeaderDict({"content-type": "application/json"}),
                body=b'"foobar"',
                stream_response=False,
            )
        )
    ]


def test_request_headers() -> None:
    adapter, send_request, _ = create_adapter(
        headers={
            "authorization": "Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ==",
            "referer": "https://www.example.com",
        }
    )

    response = adapter.request(
        "GET",
        "https://www.example.com",
        headers={"referer": "https://www.example.com/foo/bar"},
    )
    assert response == send_request.return_value

    response = adapter.request(
        "GET",
        "https://www.example.com",
        headers={"x-foo": "bar"},
    )
    assert response == send_request.return_value

    assert send_request.call_args_list == [
        call(
            HTTPRequest(
                method="GET",
                url="https://www.example.com",
                headers=HTTPHeaderDict(
                    {
                        "authorization": "Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ==",
                        "referer": "https://www.example.com/foo/bar",
                    }
                ),
                body=b"",
                stream_response=False,
            )
        ),
        call(
            HTTPRequest(
                method="GET",
                url="https://www.example.com",
                headers=HTTPHeaderDict(
                    {
                        "authorization": "Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ==",
                        "referer": "https://www.example.com",
                        "x-foo": "bar",
                    }
                ),
                body=b"",
                stream_response=False,
            )
        ),
    ]


def test_request_stream_response() -> None:
    adapter, send_request, _ = create_adapter()
    response = adapter.request("GET", "https://www.example.com", stream_response=True)
    assert response == send_request.return_value
    assert send_request.call_args_list == [
        call(
            HTTPRequest(
                method="GET",
                url="https://www.example.com",
                headers=HTTPHeaderDict(),
                body=b"",
                stream_response=True,
            )
        )
    ]


def test_request_with_interceptors() -> None:
    adapter, send_request, client = create_adapter()
    adapter.request_interceptor["inter0"] = 0
    adapter.request_interceptor["inter1"] = 1
    adapter.response_interceptor["inter2"] = 1
    adapter.response_interceptor["inter3"] = 0

    client.inter2.return_value.status_code = 200

    response = adapter.request("GET", "https://www.example.com")

    assert client.inter0.call_args_list == [
        call(
            HTTPRequest(
                method="GET",
                url="https://www.example.com",
                headers=HTTPHeaderDict(),
                body=b"",
                stream_response=False,
            ),
            adapter,
        )
    ]
    assert client.inter1.call_args_list == [
        call(
            client.inter0.return_value,
            adapter,
        )
    ]
    assert send_request.call_args_list == [
        call(
            client.inter1.return_value,
        )
    ]
    assert client.inter3.call_args_list == [
        call(
            send_request.return_value,
            adapter,
        )
    ]
    assert client.inter2.call_args_list == [
        call(
            client.inter3.return_value,
            adapter,
        )
    ]
    assert response == client.inter2.return_value


def test_request_interceptor_crash() -> None:
    adapter, _, client = create_adapter()
    adapter.response_interceptor["inter"] = 0

    class CustomError(Exception):
        pass

    client.inter.side_effect = CustomError("Interceptor crash msg")

    with pytest.raises(CustomError, match=re.escape("Interceptor crash msg")):
        adapter.request("GET", "https://www.example.com")


def test_request_with_interceptors_hierarchy() -> None:
    adapter0, _, client0 = create_adapter()
    adapter1, _, client1 = create_adapter(parent_adapter=adapter0)
    adapter2, send_request2, client2 = create_adapter(parent_adapter=adapter1)

    adapter0.request_interceptor["inter0"] = 0
    adapter0.request_interceptor["inter1"] = -1
    adapter0.request_interceptor["inter2"] = -2
    adapter1.request_interceptor["inter1"] = 1
    adapter2.request_interceptor["inter2"] = 2

    response = adapter2.request("GET", "https://www.example.com")

    assert client0.inter0.call_args_list == [
        call(
            HTTPRequest(
                method="GET",
                url="https://www.example.com",
                headers=HTTPHeaderDict(),
                body=b"",
                stream_response=False,
            ),
            adapter2,
        )
    ]
    assert client1.inter1.call_args_list == [
        call(
            client0.inter0.return_value,
            adapter2,
        )
    ]
    assert client2.inter2.call_args_list == [
        call(
            client1.inter1.return_value,
            adapter2,
        )
    ]
    assert send_request2.call_args_list == [
        call(
            client2.inter2.return_value,
        )
    ]
    assert response == send_request2.return_value


@pytest.mark.parametrize(
    "method", ["get", "options", "head", "post", "put", "patch", "delete"]
)
def test_adapter_request_sugar(method: str) -> None:
    adapter, send_request, _ = create_adapter()
    request_with_method = getattr(adapter, method)

    response = request_with_method(
        "https://www.example.com/foo/bar",
        body="foobar",
        body_encoding=HTTPBodyEncoding.JSON,
        headers={
            "authorization": "Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ==",
            "referer": "https://www.example.com/",
        },
        stream_response=True,
    )
    assert response == send_request.return_value
    assert send_request.call_args_list == [
        call(
            HTTPRequest(
                method=method.upper(),
                url="https://www.example.com/foo/bar",
                headers=HTTPHeaderDict(
                    {
                        "authorization": "Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ==",
                        "referer": "https://www.example.com/",
                        "content-type": "application/json",
                    }
                ),
                body=b'"foobar"',
                stream_response=True,
            )
        )
    ]


@pytest.mark.parametrize("status_code", [204, 301, 404, 500])
def test_invalid_status_code(status_code: int) -> None:
    adapter, send_request, _ = create_adapter()
    send_request.return_value.status_code = status_code

    with pytest.raises(
        HTTPStatusCodeError, match=f"^Unexpected status code: {status_code}$"
    ) as excinfo:
        adapter.request("GET", "https://www.example.com")
    assert excinfo.value.status_code == status_code

    with pytest.raises(
        HTTPStatusCodeError, match=f"^Unexpected status code: {status_code}$"
    ) as excinfo:
        adapter.get("https://www.example.com")
    assert excinfo.value.status_code == status_code

    expected_status_codes_list: List[Union[int, str, Tuple[int, int]]] = [
        status_code,
        str(status_code),
        "xxx",
        (999, status_code),
    ]

    for expected_status_codes in expected_status_codes_list:
        adapter.request(
            "GET",
            "https://www.example.com",
            expected_status_codes=expected_status_codes,
        )
        adapter.get(
            "https://www.example.com",
            expected_status_codes=expected_status_codes,
        )


def test_adapter_context_manager() -> None:
    adapter, send_request, _ = create_adapter()

    def do_send_request(_: HTTPRequest) -> HTTPResponse:
        return FakeResponse()

    send_request.side_effect = do_send_request

    with adapter.get("https://www.example.com") as response:
        assert isinstance(response, FakeResponse)

    with pytest.raises(HTTPContextError) as excinfo:  # noqa: PT012,SIM117
        with adapter.get("https://www.example.com") as response:
            raise ValueError("oops")

    exception = excinfo.value
    assert str(exception) == "ValueError: oops"
    assert exception.request == HTTPRequest(
        method="GET",
        url="https://www.example.com",
        headers=HTTPHeaderDict(),
        body=b"",
        stream_response=False,
    )
    assert isinstance(exception.response, FakeResponse)
    assert isinstance(exception.__context__, ValueError)
