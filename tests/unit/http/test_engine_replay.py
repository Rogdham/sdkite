from dataclasses import replace
from pathlib import Path
import re
from typing import Dict, cast

import pytest

from sdkite.http import HTTPHeaderDict, HTTPRequest
from sdkite.http.engine_replay import (
    HTTPEngineReplay,
    HTTPResponseReplay,
    _RecordedResponse,
)

REPLAY_PATH = Path(__file__).parent / "engine_replay"


def test_response() -> None:
    recorded_response: _RecordedResponse = {
        "status_code": 200,
        "reason": "OK",
        "headers": {"content-type": "application/json"},
        "body": [b'{"msg":', b" 4", b"2}"],
    }
    expected_headers = HTTPHeaderDict({"content-type": "application/json"})

    response_replay = HTTPResponseReplay(recorded_response)
    with pytest.raises(
        ValueError,
        match=re.escape("The 'raw' attribute is not available with the replay engine"),
    ):
        response_replay.raw  # pylint: disable=pointless-statement  # noqa: B018
    assert response_replay.status_code == 200
    assert response_replay.reason == "OK"
    assert response_replay.headers == expected_headers

    response_replay = HTTPResponseReplay(recorded_response)
    data_stream = response_replay.data_stream
    assert next(data_stream) == b'{"msg":'
    assert next(data_stream) == b" 4"
    assert next(data_stream) == b"2}"
    assert next(data_stream, None) is None

    response_replay = HTTPResponseReplay(recorded_response)
    assert next(response_replay.data_stream) == b'{"msg":'
    assert next(response_replay.data_stream) == b" 4"
    assert next(response_replay.data_stream) == b"2}"
    assert next(response_replay.data_stream, None) is None

    response_replay = HTTPResponseReplay(recorded_response)
    assert response_replay.data_bytes == b'{"msg": 42}'
    with pytest.raises(
        ValueError,
        match=re.escape(
            "The data_xxx attributes can be only accessed once with the replay engine"
        ),
    ):
        response_replay.data_bytes  # pylint: disable=pointless-statement  # noqa: B018

    response_replay = HTTPResponseReplay(recorded_response)
    assert response_replay.data_str == '{"msg": 42}'
    with pytest.raises(
        ValueError,
        match=re.escape(
            "The data_xxx attributes can be only accessed once with the replay engine"
        ),
    ):
        response_replay.data_str  # pylint: disable=pointless-statement  # noqa: B018

    response_replay = HTTPResponseReplay(recorded_response)
    assert response_replay.data_json == {"msg": 42}
    assert response_replay.data_json == {"msg": 42}

    # modify headers
    response_replay = HTTPResponseReplay(recorded_response)
    response_replay.headers["content-type"] = "new"
    assert response_replay.headers["content-type"] == "new"
    response_replay = HTTPResponseReplay(recorded_response)
    assert response_replay.headers == expected_headers

    # modify json
    response_replay = HTTPResponseReplay(recorded_response)
    data = cast(Dict[str, int], response_replay.data_json)
    data["msg"] = 1337
    assert response_replay.data_json == {"msg": 1337}
    response_replay = HTTPResponseReplay(recorded_response)
    assert response_replay.data_json == {"msg": 42}


def test_response_replace() -> None:
    recorded_response: _RecordedResponse = {
        "status_code": 200,
        "reason": "OK",
        "headers": {"content-type": "application/json"},
        "body": [b'{"msg":', b" 4", b"2}"],
    }
    response_replay = HTTPResponseReplay(recorded_response)
    assert response_replay.status_code == 200
    assert response_replay.reason == "OK"
    assert response_replay.headers == HTTPHeaderDict(
        {"content-type": "application/json"}
    )
    assert response_replay.data_json == {"msg": 42}

    response_replay2 = response_replay.replace(status_code=500)
    assert response_replay2.status_code == 500
    assert response_replay2.reason == "OK"
    assert response_replay2.headers == HTTPHeaderDict(
        {"content-type": "application/json"}
    )
    assert response_replay2.data_json == {"msg": 42}

    response_replay2 = response_replay.replace(reason="ALLGOOD")
    assert response_replay2.status_code == 200
    assert response_replay2.reason == "ALLGOOD"
    assert response_replay2.headers == HTTPHeaderDict(
        {"content-type": "application/json"}
    )
    assert response_replay2.data_json == {"msg": 42}

    response_replay2 = response_replay.replace(headers={"foo": "bar"})
    assert response_replay2.status_code == 200
    assert response_replay2.reason == "OK"
    assert response_replay2.headers == HTTPHeaderDict({"foo": "bar"})
    assert response_replay2.data_json == {"msg": 42}

    response_replay2 = response_replay.replace(body=b"42")
    assert response_replay2.status_code == 200
    assert response_replay2.reason == "OK"
    assert response_replay2.headers == HTTPHeaderDict(
        {"content-type": "application/json"}
    )
    assert response_replay2.data_json == 42

    response_replay2 = response_replay.replace(body=[b"13", b"37"])
    assert response_replay2.status_code == 200
    assert response_replay2.reason == "OK"
    assert response_replay2.headers == HTTPHeaderDict(
        {"content-type": "application/json"}
    )
    assert response_replay2.data_json == 1337


def test_replay_existing() -> None:
    engine = HTTPEngineReplay([REPLAY_PATH / "base"])
    request = HTTPRequest(
        method="GET",
        url="https://example.com/",
        headers=HTTPHeaderDict(),
        body=b"",
        stream_response=False,
    )
    for response in [engine(request), engine(replace(request, stream_response=True))]:
        assert response.status_code == 200
        assert response.reason == "OK"
        assert response.headers == HTTPHeaderDict({"server": "nginx"})
        assert response.data_json == {"msg": 42}

    with pytest.raises(
        ValueError,
        match=re.escape(
            "No response have been recorded for request: {"
            "'method': 'HEAD', "
            "'url': 'https://example.com/', "
            "'headers': {}, "
            "'body': b''}"
        ),
    ):
        engine(replace(request, method="HEAD"))

    with pytest.raises(
        ValueError,
        match=re.escape(
            "No response have been recorded for request: {"
            "'method': 'GET', "
            "'url': 'https://example.com/foobar', "
            "'headers': {}, "
            "'body': b''}"
        ),
    ):
        engine(replace(request, url="https://example.com/foobar"))

    with pytest.raises(
        ValueError,
        match=re.escape(
            "No response have been recorded for request: {"
            "'method': 'GET', "
            "'url': 'https://example.com/', "
            "'headers': {'foo': 'bar'}, "
            "'body': b''}"
        ),
    ):
        engine(replace(request, headers=HTTPHeaderDict({"foo": "bar"})))

    with pytest.raises(
        ValueError,
        match=re.escape(
            "No response have been recorded for request: {"
            "'method': 'GET', "
            "'url': 'https://example.com/', "
            "'headers': {}, "
            "'body': b'foobar'}"
        ),
    ):
        engine(replace(request, body=b"foobar"))


@pytest.mark.parametrize("url_end", ["wrong_ext", "in_subfolder"])
def test_replay_miss(url_end: str) -> None:
    engine = HTTPEngineReplay([REPLAY_PATH / "base"])
    request = HTTPRequest(
        method="GET",
        url=f"https://example.com/{url_end}",
        headers=HTTPHeaderDict(),
        body=b"",
        stream_response=False,
    )
    with pytest.raises(
        ValueError,
        match=re.escape(
            "No response have been recorded for request: {"
            "'method': 'GET', "
            f"'url': 'https://example.com/{url_end}', "
            "'headers': {}, "
            "'body': b''}"
        ),
    ):
        engine(request)


def test_replay_multiple_paths() -> None:
    engine = HTTPEngineReplay([REPLAY_PATH / "base", REPLAY_PATH / "extra"])
    request = HTTPRequest(
        method="GET",
        url="https://example.com/",
        headers=HTTPHeaderDict(),
        body=b"",
        stream_response=False,
    )

    # only in base
    response = engine(request)
    assert response.data_json == {"msg": 42}

    # only in extra
    response = engine(replace(request, url="https://example.com/bar"))
    assert response.data_json == {"msg": 13}

    # in both base and extra: keep extra
    response = engine(replace(request, url="https://example.com/foo"))
    assert response.data_json == {"msg": 37}

    # in none
    with pytest.raises(
        ValueError,
        match=re.escape(
            "No response have been recorded for request: {"
            "'method': 'GET', "
            "'url': 'https://example.com/miss', "
            "'headers': {}, "
            "'body': b''}"
        ),
    ):
        engine(replace(request, url="https://example.com/miss"))


def test_replay_encoding() -> None:
    data = bytes(range(256))
    engine = HTTPEngineReplay([REPLAY_PATH / "base"])
    request = HTTPRequest(
        method="POST",
        url="https://example.com/encoding",
        headers=HTTPHeaderDict(),
        body=data,
        stream_response=False,
    )
    response = engine(request)
    assert response.data_bytes == data[::-1]


def test_replay_with_modifiers() -> None:
    def replay_request_modifier(request: HTTPRequest) -> HTTPRequest:
        assert request.url == "https://example.com/auth"
        request.url = "https://example.com/foo"
        del request.headers["authorization"]
        return request

    def replay_response_modifier(response: HTTPResponseReplay) -> HTTPResponseReplay:
        return response.replace(body=b'{"msg": 1337}')

    engine = HTTPEngineReplay(
        [REPLAY_PATH / "base"],
        replay_request_modifier=replay_request_modifier,
        replay_response_modifier=replay_response_modifier,
    )
    request = HTTPRequest(
        method="GET",
        url="https://example.com/auth",
        headers=HTTPHeaderDict({"Authorization": "Basic dXNlcjpwYXNzd29yZA=="}),
        body=b"",
        stream_response=False,
    )
    response = engine(request)
    assert response.status_code == 200
    assert response.reason == "OK"
    assert response.headers == HTTPHeaderDict({"server": "nginx"})
    assert response.data_json == {"msg": 1337}
