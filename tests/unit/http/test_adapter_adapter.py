from typing import Dict, Optional, Tuple
from unittest.mock import Mock, call

import pytest

from sdkite.http import HTTPAdapter, HTTPBodyEncoding, HTTPHeaderDict, HTTPRequest


def create_adapter(
    url: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    parent_adapter: Optional[HTTPAdapter] = None,
) -> Tuple[HTTPAdapter, Mock, Mock]:
    # pylint: disable=protected-access
    send_request = Mock()
    adapter = HTTPAdapter(send_request)
    adapter._attr_name = "http"
    client = Mock()
    client.http = adapter
    adapter._clients = (client,)
    if parent_adapter:
        adapter._clients = parent_adapter._clients + adapter._clients
    adapter.url = url
    adapter.headers = HTTPHeaderDict(headers)
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
    "base_url, url",
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


def test_no_request_url() -> None:
    adapter, _, _ = create_adapter()
    with pytest.raises(ValueError):
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
