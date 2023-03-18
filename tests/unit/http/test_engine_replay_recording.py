from pathlib import Path
import re
import time
from typing import Set

import pytest
from requests_mock import Mocker, NoMockAddress

from sdkite.http import HTTPError, HTTPHeaderDict, HTTPRequest
from sdkite.http.engine_replay import HTTPEngineReplay, HTTPResponseReplay

REPLAY_PATH = Path(__file__).parent / "engine_replay"


@pytest.fixture(autouse=True)
def _patched_time(monkeypatch: pytest.MonkeyPatch) -> None:
    def mocked_time() -> int:
        return 1234567890

    monkeypatch.setattr(time, "time", mocked_time)


def list_files(src: Path) -> Set[Path]:
    return {path.relative_to(src) for path in src.rglob("*") if path.is_file()}


def test_recording(tmp_path: Path, requests_mock: Mocker) -> None:
    original_get_root_data = (REPLAY_PATH / "base" / "get_root.json").read_bytes()
    original_get_foo_data = (REPLAY_PATH / "base" / "get_foo.json").read_bytes()
    (tmp_path / "aaa").mkdir(parents=True)
    (tmp_path / "bbb").mkdir(parents=True)
    (tmp_path / "aaa" / "get_root.json").write_bytes(original_get_root_data)
    (tmp_path / "aaa" / "get_foo.json").write_bytes(original_get_foo_data)

    engine = HTTPEngineReplay([tmp_path / "aaa", tmp_path / "bbb"], recording=True)

    requests_mock.register_uri(
        # request
        "GET",
        "https://example.com/foo",
        # response
        content=b'{"msg": 13}',
        reason="OK",
        headers={"server": "nginx"},
    )
    requests_mock.register_uri(
        # request
        "GET",
        "https://example.com/bar",
        # response
        content=b'{"msg": 37}',
        reason="OK",
        headers={"server": "nginx"},
    )

    # missing
    request = HTTPRequest(
        method="GET",
        url="https://example.com/bar",
        headers=HTTPHeaderDict(),
        body=b"",
        stream_response=False,
    )
    response = engine(request)
    assert response.status_code == 200
    assert response.reason == "OK"
    assert response.headers == HTTPHeaderDict({"server": "nginx"})
    assert response.data_json == {"msg": 37}
    assert list_files(tmp_path) == {
        Path() / "aaa" / "get_root.json",
        Path() / "aaa" / "get_foo.json",
        Path() / "bbb" / "1234567890_get_https___example_com_bar.json",
    }
    assert (
        (tmp_path / "bbb" / "1234567890_get_https___example_com_bar.json").read_bytes()
        == rb"""{
  "request": {
    "method": "GET",
    "url": "https://example.com/bar",
    "headers": {},
    "body": ""
  },
  "response": {
    "status_code": 200,
    "reason": "OK",
    "headers": {
      "server": "nginx"
    },
    "body": [
      "{\"msg\": 37}"
    ]
  }
}
"""
    )

    # existing
    request = HTTPRequest(
        method="GET",
        url="https://example.com/foo",
        headers=HTTPHeaderDict(),
        body=b"",
        stream_response=False,
    )
    response = engine(request)
    assert response.status_code == 200
    assert response.reason == "OK"
    assert response.headers == HTTPHeaderDict({"server": "nginx"})
    assert response.data_json == {"msg": 13}
    assert list_files(tmp_path) == {
        Path() / "aaa" / "get_root.json",
        Path() / "aaa" / "get_foo.json",
        Path() / "bbb" / "1234567890_get_https___example_com_bar.json",
        Path() / "bbb" / "1234567890_get_https___example_com_foo.json",
    }
    assert (tmp_path / "aaa" / "get_foo.json").read_bytes() == original_get_foo_data
    assert (
        (tmp_path / "bbb" / "1234567890_get_https___example_com_foo.json").read_bytes()
        == rb"""{
  "request": {
    "method": "GET",
    "url": "https://example.com/foo",
    "headers": {},
    "body": ""
  },
  "response": {
    "status_code": 200,
    "reason": "OK",
    "headers": {
      "server": "nginx"
    },
    "body": [
      "{\"msg\": 13}"
    ]
  }
}
"""
    )

    # crash
    request = HTTPRequest(
        method="GET",
        url="https://example.com/",
        headers=HTTPHeaderDict(),
        body=b"",
        stream_response=False,
    )
    with pytest.raises(
        HTTPError,
        match=re.escape("NoMockAddress: No mock address: GET https://example.com/"),
    ) as excinfo:
        response = engine(request)
    assert (  # pylint: disable=unidiomatic-typecheck
        type(excinfo.value.__context__) is NoMockAddress
    )


@pytest.mark.parametrize("recording", [True, False])
def test_recording_modifiers(
    tmp_path: Path, requests_mock: Mocker, recording: bool
) -> None:
    expected_recording = rb"""{
  "request": {
    "method": "GET",
    "url": "https://example.com/foo",
    "headers": {
      "Authorization": "Bearer fake_creds"
    },
    "body": ""
  },
  "response": {
    "status_code": 200,
    "reason": "OK",
    "headers": {
      "server": "nginx"
    },
    "body": [
      "{\"msg\": \"saved\"}"
    ]
  }
}
"""

    if recording:
        requests_mock.register_uri(
            # request
            "GET",
            "https://example.com/foo",
            request_headers={"authorization": "Bearer valid_creds"},
            # response
            content=b'{"msg": "real"}',
            reason="OK",
            headers={"server": "nginx"},
        )
    else:
        (tmp_path / "recorded.json").write_bytes(expected_recording)

    def replay_request_modifier(request: HTTPRequest) -> HTTPRequest:
        if "Authorization" in request.headers:
            request.headers["Authorization"] = request.headers["Authorization"].replace(
                "some_creds", "fake_creds"
            )
        return request

    response_id = -1

    def replay_response_modifier(response: HTTPResponseReplay) -> HTTPResponseReplay:
        nonlocal response_id
        response_id += 1
        return response.replace(
            body=response.data_bytes.replace(b"saved", b"modified%d" % response_id)
        )

    def recording_request_modifier(request: HTTPRequest) -> HTTPRequest:
        if "Authorization" in request.headers:
            request.headers["Authorization"] = request.headers["Authorization"].replace(
                "some_creds", "valid_creds"
            )
        return request

    def recording_response_modifier(response: HTTPResponseReplay) -> HTTPResponseReplay:
        return response.replace(body=response.data_bytes.replace(b"real", b"saved"))

    engine = HTTPEngineReplay(
        [tmp_path],
        recording=recording,
        replay_request_modifier=replay_request_modifier,
        replay_response_modifier=replay_response_modifier,
        recording_request_modifier=recording_request_modifier,
        recording_response_modifier=recording_response_modifier,
    )

    request = HTTPRequest(
        method="GET",
        url="https://example.com/foo",
        headers=HTTPHeaderDict({"Authorization": "Bearer some_creds"}),
        body=b"",
        stream_response=False,
    )
    response = engine(request)
    assert response.status_code == 200
    assert response.reason == "OK"
    assert response.headers == HTTPHeaderDict({"server": "nginx"})
    assert response.data_json == {"msg": "modified0"}

    # no mutations in request
    assert request == HTTPRequest(
        method="GET",
        url="https://example.com/foo",
        headers=HTTPHeaderDict({"Authorization": "Bearer some_creds"}),
        body=b"",
        stream_response=False,
    )

    if recording:
        assert (
            tmp_path / "1234567890_get_https___example_com_foo.json"
        ).read_bytes() == expected_recording

    # response unmodified
    response = engine(request)
    assert response.data_json == {"msg": "modified1"}
