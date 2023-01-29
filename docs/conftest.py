from os import chdir, getcwd
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple, cast

import pytest
from requests_mock import Mocker

from sdkite import Client
from sdkite.http import HTTPRequest, HTTPResponse


@pytest.fixture(scope="module", autouse=True)
def import_pytest(doctest_namespace: Dict[str, object]) -> None:
    doctest_namespace["Iterator"] = Iterator
    doctest_namespace["Path"] = Path

    doctest_namespace["Client"] = Client

    def list_spells(
        max_price: int,
        offset: int = 0,
        page: Optional[int] = None,
    ) -> List[str]:
        assert max_price == 50
        limit = 3
        if page is not None:
            offset = page * limit
        return [
            "Crushing Burden Touch",
            "Great Burden of Sin",
            "Heavy Burden",
            "Strong Feather",
            "Tinur's Hoptoad",
            "Ulms's Juicedaw's Feather",
            "Far Silence",
            "Soul Trap",
        ][offset:][:limit]

    def list_spells_with_ref(
        max_price: Optional[int] = 50,
        cursor: Optional[str] = None,
    ) -> Tuple[List[str], Optional[str]]:
        assert max_price == 50
        cursors = [None, "57656c636", "f6d652074", "6f2042616", "c6d6f7261"]
        index = cursors.index(cursor)
        return list_spells(max_price, page=index), cursors[index + 1]

    class ExampleEngine:
        def __init__(self, *_: object, **__: object) -> None:
            pass

        def __call__(self, request: HTTPRequest) -> HTTPResponse:
            raise NotImplementedError

    doctest_namespace["list_spells"] = list_spells
    doctest_namespace["list_spells_with_ref"] = list_spells_with_ref
    doctest_namespace["ExampleEngine"] = ExampleEngine


@pytest.fixture(autouse=True)
def patch_http(requests_mock: Mocker) -> None:
    #
    # quickstart
    #
    requests_mock.register_uri(
        "GET",
        "https://api.example.com/world/npc/interact?name=ranis",
        text="Have you found the Telvanni spy?",
    )
    requests_mock.register_uri(
        "POST",
        "https://api.example.com/world/npc/search",
        additional_matcher=lambda request: cast(
            bool,
            request.json() == {"city": "Balmora", "faction": "Mage", "min_level": 8},
        ),
        json=["marayn", "masalinie", "ranis"],
    )
    requests_mock.register_uri(
        "GET",
        "https://api.example.com/world/book/content?id=bk_words_of_the_wind",
        request_headers={"Authorization": "Basic TmVyZXZhcmluZTpJbmNhcm5hdGU="},
        text="Words of the Wind\n\nA volume of verse collected from...",
    )

    #
    # http_auth
    #
    requests_mock.register_uri(
        "GET",
        "https://api.example.com/whoami",
        request_headers={"Authorization": "Basic QWxpY2U6VzBuZGVybEBuZA=="},
        text="Welcome Alice!",
    )
    requests_mock.register_uri(
        "GET",
        "https://api.example.com/noauth",
        additional_matcher=lambda request: "Authorization" not in request.headers,
        text="The /noauth endpoint has been called without auth",
    )


@pytest.fixture(autouse=True)
def create_replay_store(tmp_path: Path) -> None:
    store = tmp_path / "replay"
    store.mkdir()
    (store / "ping.json").write_bytes(
        rb"""{
  "request": {
    "method": "GET",
    "url": "https://api.example.com/ping",
    "headers": {},
    "body": ""
  },
  "response": {
    "status_code": 200,
    "reason": "OK",
    "headers": {},
    "body": "pong"
  }
}
"""
    )


@pytest.fixture(autouse=True)
def change_directory(tmp_path: Path) -> Iterator[None]:
    cwd = getcwd()
    try:
        chdir(tmp_path)
        yield
    finally:
        chdir(cwd)
