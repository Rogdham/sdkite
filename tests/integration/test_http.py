from pathlib import Path
import sys
from typing import Any, List, cast

import pytest
from requests_mock import Mocker

from sdkite import Client, Pagination, paginated
from sdkite.http import BasicAuth, HTTPAdapterSpec, HTTPRequest, NoAuth
from sdkite.http.engine_replay import HTTPEngineReplay, HTTPResponseReplay

if sys.version_info < (3, 8):  # pragma: no cover
    from typing_extensions import TypedDict
else:  # pragma: no cover
    from typing import TypedDict


REPLAY_PATH = Path(__file__).parent / "recorded"


class ApiPublic(Client):
    _http = HTTPAdapterSpec(url="public")
    _auth = NoAuth(_http)

    def version(self) -> str:
        response = self._http.get("version")
        return response.data_str


class User(TypedDict):
    name: str
    age: int


class ApiUsers(Client):
    _http = HTTPAdapterSpec(url="users", headers={"X-Toto": "Abc"})

    def get(self, user_id: int) -> User:
        response = self._http.get(str(user_id))
        return cast(User, response.data_json)

    @paginated(page=1)
    def get_all(self, pagination: Pagination) -> List[User]:
        response = self._http.get(f"all/{pagination.page}")
        return cast(List[User], response.data_json)


class Api(Client):
    _http = HTTPAdapterSpec()
    _auth = BasicAuth(_http, username="tests")

    public: ApiPublic
    users: ApiUsers

    def __init__(self, url: str, password: str) -> None:
        super().__init__()
        self._http.url = url
        self._auth.password = password


@pytest.fixture
def _mock_http_requests(requests_mock: Mocker) -> None:
    common_response: Any = {
        "reason": "OK",
        "headers": {"server": "nginx"},
    }

    requests_mock.register_uri(
        # request
        "GET",
        "https://www.example.com/api/v1/public/version",
        additional_matcher=lambda request: "Authorization" not in request.headers,
        # response
        content=b"1.2.3",
        **common_response,
    )

    requests_mock.register_uri(
        # request
        "GET",
        "https://www.example.com/api/v1/users/1337",
        request_headers={"authorization": "Basic dGVzdHM6czNjcjN0"},
        # response
        content=b'{"name":"John Doe","age":42}',
        **common_response,
    )

    requests_mock.register_uri(
        # request
        "GET",
        "https://www.example.com/api/v1/users/all/1",
        request_headers={"authorization": "Basic dGVzdHM6czNjcjN0"},
        # response
        content=b'[{"name":"John Doe","age":42},{"name":"Alice Doe","age":41}]',
        **common_response,
    )
    requests_mock.register_uri(
        # request
        "GET",
        "https://www.example.com/api/v1/users/all/2",
        request_headers={"authorization": "Basic dGVzdHM6czNjcjN0"},
        # response
        content=b'[{"name":"Bob Doe","age":10},{"name":"Carole Doe","age":12}]',
        **common_response,
    )
    requests_mock.register_uri(
        # request
        "GET",
        "https://www.example.com/api/v1/users/all/3",
        request_headers={"authorization": "Basic dGVzdHM6czNjcjN0"},
        # response
        content=b"[]",
        **common_response,
    )


@pytest.mark.usefixtures("_mock_http_requests")
def test_http() -> None:
    client = Api("https://www.example.com/api/v1", "s3cr3t")

    assert client.public.version() == "1.2.3"

    user = client.users.get(1337)
    assert user == User(name="John Doe", age=42)

    users = list(client.users.get_all())
    assert users == [
        User(name="John Doe", age=42),
        User(name="Alice Doe", age=41),
        User(name="Bob Doe", age=10),
        User(name="Carole Doe", age=12),
    ]


def replay_request_modifier(request: HTTPRequest) -> HTTPRequest:
    if "Authorization" in request.headers:
        request.headers["Authorization"] = "Basic redacted"
    return request


def test_http_replay_replay(
    # notice how we don't use `_mock_http_requests` here
    # still patching requests just in case
    requests_mock: Mocker,  # pylint: disable=unused-argument # noqa: ARG001
) -> None:
    Api._http.set_engine(  # pylint: disable=protected-access
        HTTPEngineReplay,
        [REPLAY_PATH],
        replay_request_modifier=replay_request_modifier,
    )

    client = Api(
        "https://www.example.com/api/v1",
        "whatever",  # password is ignored
    )

    assert client.public.version() == "1.2.3"

    user = client.users.get(1337)
    assert user == User(name="John Doe", age=42)

    users = list(client.users.get_all())
    assert users == [
        User(name="John Doe", age=42),
        User(name="Alice Doe", age=41),
        User(name="Bob Doe", age=10),
        User(name="Carole Doe", age=12),
    ]


@pytest.mark.usefixtures("_mock_http_requests")
def test_http_replay_record(tmp_path: Path) -> None:
    def recording_response_modifier(response: HTTPResponseReplay) -> HTTPResponseReplay:
        return response.replace(
            headers={
                **response.headers,
                "server": "apache",
            }
        )

    def recording_compute_basename(request: HTTPRequest, _: HTTPResponseReplay) -> str:
        prefix = "https://www.example.com/api/v1/"
        assert request.url.startswith(prefix)
        return request.url[len(prefix) :].replace("/", "_")

    Api._http.set_engine(  # pylint: disable=protected-access
        HTTPEngineReplay,
        [tmp_path],
        recording=True,
        replay_request_modifier=replay_request_modifier,
        recording_response_modifier=recording_response_modifier,
        recording_compute_basename=recording_compute_basename,
    )

    client = Api("https://www.example.com/api/v1", "s3cr3t")

    assert client.public.version() == "1.2.3"

    user = client.users.get(1337)
    assert user == User(name="John Doe", age=42)

    users = list(client.users.get_all())
    assert users == [
        User(name="John Doe", age=42),
        User(name="Alice Doe", age=41),
        User(name="Bob Doe", age=10),
        User(name="Carole Doe", age=12),
    ]

    expected_paths = {path.relative_to(REPLAY_PATH) for path in REPLAY_PATH.rglob("*")}
    assert {
        path.relative_to(tmp_path) for path in tmp_path.rglob("*")
    } == expected_paths

    for path in expected_paths:
        assert (tmp_path / path).read_bytes() == (REPLAY_PATH / path).read_bytes(), path
