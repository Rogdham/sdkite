from requests import Response
from requests_mock import Mocker

from sdkite.http import HTTPHeaderDict, HTTPRequest, HTTPResponse
from sdkite.http.impl_requests import RequestsImpl, RequestsResponse


def test_requests_impl(requests_mock: Mocker) -> None:
    requests_mock.register_uri(
        # request
        "POST",
        "https://www.example.com/foo/bar",
        request_headers={"X-Foo": "Uvw"},
        # response
        content=b'{"hello":"world"}',
        reason="OK",
        headers={"X-Bar": "Xyz"},
    )

    impl = RequestsImpl()
    response = impl(
        HTTPRequest(
            method="POST",
            url="https://www.example.com/foo/bar",
            headers=HTTPHeaderDict({"X-Foo": "Uvw"}),
            body=b"hello",
            stream_response=False,
        )
    )

    request = requests_mock.request_history[0]
    assert request.scheme == "https"
    assert request.hostname == "www.example.com"
    assert request.port == 443
    assert request.path == "/foo/bar"
    assert not request.query
    assert request.text == "hello"
    assert not request.stream
    assert not request.allow_redirects

    assert isinstance(response, HTTPResponse)
    assert isinstance(response, RequestsResponse)
    assert isinstance(response.raw, Response)
    assert response.status_code == 200
    assert response.reason == "OK"
    assert response.headers == HTTPHeaderDict({"X-Bar": "Xyz"})
    assert b"".join(response.data_stream) == b'{"hello":"world"}'
    assert response.data_bytes == b'{"hello":"world"}'
    assert response.data_str == '{"hello":"world"}'
    assert response.data_json == {"hello": "world"}

    # check mutability
    response.headers["aaa"] = "bbb"
    assert response.headers == HTTPHeaderDict({"X-Bar": "Xyz", "aaa": "bbb"})
    assert not list(response.data_stream)  # exhausted
    response.data_json["aaa"] = "bbb"  # type: ignore[index]
    assert response.data_json == {"hello": "world", "aaa": "bbb"}


def test_request_impl_custom_ua(requests_mock: Mocker) -> None:
    requests_mock.register_uri(
        # request
        "GET",
        "https://www.example.com/foo/bar",
        request_headers={"User-Agent": "Custom"},
    )

    impl = RequestsImpl()
    impl(
        HTTPRequest(
            method="GET",
            url="https://www.example.com/foo/bar",
            headers=HTTPHeaderDict({"User-Agent": "Custom"}),
            body=b"",
            stream_response=False,
        )
    )
