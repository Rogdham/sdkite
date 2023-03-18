from contextlib import nullcontext
import re
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, call

import pytest

from sdkite.http import (
    HTTPAdapter,
    HTTPAdapterSendRequest,
    HTTPAdapterSpec,
    HTTPBodyEncoding,
    HTTPHeaderDict,
    HTTPRequest,
    HTTPResponse,
)
from sdkite.http import adapter as adapter_module
from sdkite.http.adapter import _BeforeSleep

if TYPE_CHECKING:
    from sdkite import Client
else:
    # we want independent unit tests
    Client = object


class FakeResponse(HTTPResponse):
    def __init__(self, context: str, raw: object) -> None:
        self.context = context
        self._raw = raw

    @property
    def raw(self) -> object:
        return self._raw

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, FakeResponse)
            and self.context == other.context
            and self.raw == other.raw
        )

    def __repr__(self) -> str:
        return f"FakeResponse<{self.context}, {self.raw}>"

    status_code = 200
    reason = "Ok"
    headers = HTTPHeaderDict()
    data_stream = iter(())
    data_bytes = b""
    data_str = ""
    data_json = None


@pytest.fixture(autouse=True)
def _patched_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = Mock()
    engine.return_value = lambda request: FakeResponse("send_request", request)
    monkeypatch.setattr(adapter_module, "HTTPEngineRequests", engine)


@pytest.fixture
def patched_tenacity(monkeypatch: pytest.MonkeyPatch) -> Mock:
    tenacity = Mock()

    tenacity.Retrying.return_value = [nullcontext()]
    tenacity.stop_after_attempt.side_effect = call
    tenacity.wait_exponential_jitter.side_effect = call

    for attr in ["Retrying", "stop_after_attempt", "wait_exponential_jitter"]:
        monkeypatch.setattr(adapter_module, attr, getattr(tenacity, attr))

    return tenacity


def test_base(
    patched_tenacity: Mock,  # pylint: disable=redefined-outer-name
) -> None:
    class Klass(Client):
        _parent = None

        xxx = HTTPAdapterSpec(url="https://www.example.com/xxx")

    expected_request = HTTPRequest(
        method="GET",
        url="https://www.example.com/xxx/uvw",
        headers=HTTPHeaderDict(),
        body=b"",
        stream_response=False,
    )

    client = Klass()
    response = client.xxx.request("GET", "uvw")
    assert response == FakeResponse("send_request", expected_request)

    assert patched_tenacity.Retrying.call_args_list == [
        call(
            stop=patched_tenacity.stop_after_attempt(3),
            wait=patched_tenacity.wait_exponential_jitter(
                initial=1.0, max=60.0, jitter=1.0
            ),
            before_sleep=_BeforeSleep(None, expected_request),
            reraise=True,
        )
    ]


def test_retry_at_spec_level(
    patched_tenacity: Mock,  # pylint: disable=redefined-outer-name
) -> None:
    # these get deepcopy-ed so Mock() would not work
    retry_callback0: Any = "retry_callback0"
    retry_callback1: Any = "retry_callback1"

    class Klass(Client):
        _parent = None

        xxx = HTTPAdapterSpec(
            url="https://www.example.com/xxx",
            retry_nb_attempts=1,
            retry_wait_initial=2.0,
            retry_wait_max=3.0,
            retry_wait_jitter=4.0,
            retry_callback=retry_callback0,
        )

    expected_request = HTTPRequest(
        method="GET",
        url="https://www.example.com/xxx/uvw",
        headers=HTTPHeaderDict(),
        body=b"",
        stream_response=False,
    )

    client = Klass()

    client.xxx.request("GET", "uvw")
    assert patched_tenacity.Retrying.call_args_list == [
        call(
            stop=patched_tenacity.stop_after_attempt(1),
            wait=patched_tenacity.wait_exponential_jitter(
                initial=2.0, max=3.0, jitter=4.0
            ),
            before_sleep=_BeforeSleep(retry_callback0, expected_request),
            reraise=True,
        )
    ]
    patched_tenacity.Retrying.reset_mock()

    client.xxx.request(
        "GET",
        "uvw",
        retry_nb_attempts=6,
        retry_wait_initial=7.0,
        retry_wait_max=8.0,
        retry_wait_jitter=9.0,
        retry_callback=retry_callback1,
    )
    assert patched_tenacity.Retrying.call_args_list == [
        call(
            stop=patched_tenacity.stop_after_attempt(6),
            wait=patched_tenacity.wait_exponential_jitter(
                initial=7.0, max=8.0, jitter=9.0
            ),
            before_sleep=_BeforeSleep(retry_callback1, expected_request),
            reraise=True,
        )
    ]


def test_overidden_content_type() -> None:
    class Klass(Client):
        _parent = None

        xxx = HTTPAdapterSpec(url="https://www.example.com/xxx")

    client = Klass()
    with pytest.warns(
        UserWarning,
        match=re.escape(
            "The 'content-type' header is being overridden due to request body encoding"
            " HTTPBodyEncoding.JSON (from 'custom' to 'application/json')"
        ),
    ):
        response = client.xxx.request(
            "GET",
            headers={"Content-Type": "custom"},
            body_encoding=HTTPBodyEncoding.JSON,
        )
    assert response == FakeResponse(
        "send_request",
        HTTPRequest(
            method="GET",
            url="https://www.example.com/xxx",
            headers=HTTPHeaderDict({"content-type": "application/json"}),
            body=b"null",
            stream_response=False,
        ),
    )


def test_interceptor_method() -> None:
    class Klass(Client):
        _parent = None

        xxx = HTTPAdapterSpec(url="https://www.example.com/xxx")

        @xxx.intercept_request(0)
        def xxx_req(self, request: HTTPRequest, _: HTTPAdapter) -> HTTPRequest:
            request.headers.add("intercept", "xxx")
            return request

        @xxx.intercept_response(1)
        def xxx_resp(self, response: HTTPResponse, _: HTTPAdapter) -> HTTPResponse:
            return FakeResponse("xxx_resp", response)

    client = Klass()
    response = client.xxx.request("GET", "uvw")
    assert response == FakeResponse(
        "xxx_resp",
        FakeResponse(
            "send_request",
            HTTPRequest(
                method="GET",
                url="https://www.example.com/xxx/uvw",
                headers=HTTPHeaderDict({"intercept": "xxx"}),
                body=b"",
                stream_response=False,
            ),
        ),
    )


def test_interceptor_staticmethod() -> None:
    class Klass(Client):
        _parent = None

        xxx = HTTPAdapterSpec(url="https://www.example.com/xxx")
        yyy = HTTPAdapterSpec(url="https://www.example.com/xxx")

        @xxx.intercept_request(0)
        @staticmethod
        def xxx_req(request: HTTPRequest, _: HTTPAdapter) -> HTTPRequest:
            request.headers.add("intercept", "xxx")
            return request

        @xxx.intercept_response(1)
        @staticmethod
        def xxx_resp(response: HTTPResponse, _: HTTPAdapter) -> HTTPResponse:
            return FakeResponse("xxx_resp", response)

        @staticmethod
        @yyy.intercept_request(0)
        def yyy_intercept(request: HTTPRequest, _: HTTPAdapter) -> HTTPRequest:
            request.headers.add("intercept", "yyy")
            return request

        @staticmethod
        @yyy.intercept_response(1)
        def yyy_resp(response: HTTPResponse, _: HTTPAdapter) -> HTTPResponse:
            return FakeResponse("yyy_resp", response)

    client = Klass()
    for attr in ("xxx", "yyy"):
        response = getattr(client, attr).request("GET", "uvw")
        assert response == FakeResponse(
            f"{attr}_resp",
            FakeResponse(
                "send_request",
                HTTPRequest(
                    method="GET",
                    url="https://www.example.com/xxx/uvw",
                    headers=HTTPHeaderDict({"intercept": attr}),
                    body=b"",
                    stream_response=False,
                ),
            ),
        )


def test_interceptor_classmethod() -> None:
    class Klass(Client):
        _parent = None

        xxx = HTTPAdapterSpec(url="https://www.example.com/xxx")
        yyy = HTTPAdapterSpec(url="https://www.example.com/xxx")

        @xxx.intercept_request(0)
        @classmethod
        def xxx_req(cls, request: HTTPRequest, _: HTTPAdapter) -> HTTPRequest:
            request.headers.add("intercept", "xxx")
            return request

        @xxx.intercept_response(1)
        @classmethod
        def xxx_resp(cls, response: HTTPResponse, _: HTTPAdapter) -> HTTPResponse:
            return FakeResponse("xxx_resp", response)

        @classmethod
        @yyy.intercept_request(0)
        def yyy_intercept(cls, request: HTTPRequest, _: HTTPAdapter) -> HTTPRequest:
            request.headers.add("intercept", "yyy")
            return request

        @classmethod
        @yyy.intercept_response(1)
        def yyy_resp(cls, response: HTTPResponse, _: HTTPAdapter) -> HTTPResponse:
            return FakeResponse("yyy_resp", response)

    client = Klass()
    for attr in ("xxx", "yyy"):
        response = getattr(client, attr).request("GET", "uvw")
        assert response == FakeResponse(
            f"{attr}_resp",
            FakeResponse(
                "send_request",
                HTTPRequest(
                    method="GET",
                    url="https://www.example.com/xxx/uvw",
                    headers=HTTPHeaderDict({"intercept": attr}),
                    body=b"",
                    stream_response=False,
                ),
            ),
        )


def test_register_interceptor_existing() -> None:
    class Klass(Client):
        _parent = None

        xxx = HTTPAdapterSpec(url="https://www.example.com/xxx")

        @xxx.intercept_request(0)
        def xxx_req(self, request: HTTPRequest, _: HTTPAdapter) -> HTTPRequest:
            request.headers.add("intercept", "xxx")
            return request

        @xxx.intercept_response(1)
        def xxx_resp(self, response: HTTPResponse, _: HTTPAdapter) -> HTTPResponse:
            return FakeResponse("xxx_resp", response)

    with pytest.warns(
        UserWarning,
        match=re.escape(
            "Interceptor 'xxx_req' of 'xxx' has already been registered"
            " with order 0, ignoring new registration with order 42"
        ),
    ):
        Klass.xxx.register_interceptor("request_interceptor", "xxx_req", 42)

    with pytest.warns(
        UserWarning,
        match=re.escape(
            "Interceptor 'xxx_resp' of 'xxx' has already been registered"
            " with order 1, ignoring new registration with order 42"
        ),
    ):
        Klass.xxx.register_interceptor("response_interceptor", "xxx_resp", 42)

    client = Klass()
    response = client.xxx.request("GET", "uvw")
    assert response == FakeResponse(
        "xxx_resp",
        FakeResponse(
            "send_request",
            HTTPRequest(
                method="GET",
                url="https://www.example.com/xxx/uvw",
                headers=HTTPHeaderDict({"intercept": "xxx"}),  # only once
                body=b"",
                stream_response=False,
            ),
        ),
    )


def test_custom_engine() -> None:
    def custom_engine(param0: int, *, param1: int) -> HTTPAdapterSendRequest:
        def send_request(request: HTTPRequest) -> HTTPResponse:
            return FakeResponse(f"engine-{param0}-{param1}", request)

        return send_request

    class Klass(Client):
        _parent = None

        xxx = HTTPAdapterSpec(url="https://www.example.com/xxx")

    with pytest.raises(TypeError):
        Klass.xxx.set_engine(custom_engine)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        Klass.xxx.set_engine(custom_engine, 42)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        Klass.xxx.set_engine(custom_engine, 42, 1337)  # type: ignore[misc]
    with pytest.raises(TypeError):
        Klass.xxx.set_engine(custom_engine, param1=1337)  # type: ignore[call-arg]

    Klass.xxx.set_engine(custom_engine, 42, param1=1337)

    client = Klass()
    response = client.xxx.request("GET", "uvw")
    assert response == FakeResponse(
        "engine-42-1337",
        HTTPRequest(
            method="GET",
            url="https://www.example.com/xxx/uvw",
            headers=HTTPHeaderDict(),
            body=b"",
            stream_response=False,
        ),
    )
