import sys
from typing import List, cast

from requests_mock import Mocker

from sdkite import Client, Pagination, paginated
from sdkite.http import BasicAuth, HTTPAdapterSpec, NoAuth

if sys.version_info < (3, 8):  # pragma: no cover
    from typing_extensions import TypedDict
else:  # pragma: no cover
    from typing import TypedDict


class ApiPublic(Client):
    http = HTTPAdapterSpec(url="public")
    auth = NoAuth(http)

    def version(self) -> str:
        response = self.http.get("version")
        return response.data_str


class User(TypedDict):
    name: str
    age: int


class ApiUsers(Client):
    http = HTTPAdapterSpec(url="users", headers={"X-Toto": "Abc"})

    def get(self, user_id: int) -> User:
        response = self.http.get(str(user_id))
        return cast(User, response.data_json)

    @paginated(page=1)
    def get_all(self, pagination: Pagination) -> List[User]:
        response = self.http.get(f"all/{pagination.page}")
        return cast(List[User], response.data_json)


class Api(Client):
    http = HTTPAdapterSpec()
    auth = BasicAuth(http, username="tests")

    public: ApiPublic
    users: ApiUsers

    def __init__(self, url: str, password: str) -> None:
        super().__init__()
        self.http.url = url
        self.auth.password = password


def test_http(requests_mock: Mocker) -> None:
    requests_mock.register_uri(
        "GET",
        "https://www.example.com/api/v1/public/version",
        additional_matcher=lambda request: "Authorization" not in request.headers,
        content=b"1.2.3",
    )

    requests_mock.register_uri(
        "GET",
        "https://www.example.com/api/v1/users/1337",
        request_headers={"authorization": "Basic dGVzdHM6czNjcjN0"},
        content=b'{"name":"John Doe","age":42}',
    )

    requests_mock.register_uri(
        "GET",
        "https://www.example.com/api/v1/users/all/1",
        request_headers={"authorization": "Basic dGVzdHM6czNjcjN0"},
        content=b'[{"name":"John Doe","age":42},{"name":"Alice Doe","age":41}]',
    )
    requests_mock.register_uri(
        "GET",
        "https://www.example.com/api/v1/users/all/2",
        request_headers={"authorization": "Basic dGVzdHM6czNjcjN0"},
        content=b'[{"name":"Bob Doe","age":10},{"name":"Carole Doe","age":12}]',
    )
    requests_mock.register_uri(
        "GET",
        "https://www.example.com/api/v1/users/all/3",
        request_headers={"authorization": "Basic dGVzdHM6czNjcjN0"},
        content=b"[]",
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
