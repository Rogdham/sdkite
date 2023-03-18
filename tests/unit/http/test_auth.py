from unittest.mock import Mock, call

from sdkite.http import BasicAuth, HTTPHeaderDict, HTTPRequest, NoAuth


def test_basic_auth() -> None:
    class WithBasicAuth:
        http = Mock()
        auth = BasicAuth(http, "user", "password")

    assert WithBasicAuth.http.method_calls == [
        call.register_interceptor("request_interceptor", "auth", 0),
    ]

    client0 = WithBasicAuth()
    client1 = WithBasicAuth()
    adapter = Mock()

    # modify creds on one client instance
    client1.auth.username = "Alice"
    client1.auth.password = "$ecr3t"  # noqa: S105

    # did not modify creds on class instance
    assert WithBasicAuth.auth.username == "user"
    assert WithBasicAuth.auth.password == "password"  # noqa: S105

    # did not modify creds on other client instance
    assert client0.auth.username == "user"
    assert client0.auth.password == "password"  # noqa: S105

    for i, client, cred in [
        (0, client0, "dXNlcjpwYXNzd29yZA=="),
        (1, client1, "QWxpY2U6JGVjcjN0"),
    ]:
        request = HTTPRequest(
            method="GET",
            url="https://www.example.com",
            headers=HTTPHeaderDict({"foo": "bar"}),
            body=b"",
            stream_response=False,
        )
        modified_request = client.auth(request, adapter)
        assert modified_request == HTTPRequest(
            method="GET",
            url="https://www.example.com",
            headers=HTTPHeaderDict(
                {
                    "foo": "bar",
                    "Authorization": f"Basic {cred}",
                }
            ),
            body=b"",
            stream_response=False,
        ), f"client {i}"
        assert not adapter.method_calls, f"client {i}"


def test_basic_auth_encoding() -> None:
    class WithBasicAuth:
        http = Mock()
        auth = BasicAuth(http, "🥸", "🔑")

    client = WithBasicAuth()
    adapter = Mock()

    request = HTTPRequest(
        method="GET",
        url="https://www.example.com",
        headers=HTTPHeaderDict(),
        body=b"",
        stream_response=False,
    )
    modified_request = client.auth(request, adapter)
    assert modified_request == HTTPRequest(
        method="GET",
        url="https://www.example.com",
        headers=HTTPHeaderDict({"Authorization": "Basic 8J+luDrwn5SR"}),
        body=b"",
        stream_response=False,
    )


def test_no_auth() -> None:
    class WithNoAuth:
        http = Mock()
        auth = NoAuth(http)

    assert WithNoAuth.http.method_calls == [
        call.register_interceptor("request_interceptor", "auth", 0),
    ]

    client = WithNoAuth()
    adapter = Mock()

    request = HTTPRequest(
        method="GET",
        url="https://www.example.com",
        headers=HTTPHeaderDict({"foo": "bar"}),
        body=b"",
        stream_response=False,
    )
    modified_request = client.auth(request, adapter)
    assert modified_request == request
    assert not adapter.method_calls
