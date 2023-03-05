from itertools import chain
import re
from typing import Iterable, List, Set, Tuple, Union

import pytest

from sdkite.http.utils import build_status_code_check

_CASES_DESCRIPTIONS: List[
    Tuple[str, Union[int, str, Iterable[Union[int, str]]], Iterable[int]]
] = [
    ("int", 200, [200]),
    ("str_exact", "200", [200]),
    ("str_2xx", "2xx", range(200, 300)),
    ("str_x00", "x00", range(0, 1000, 100)),
    ("list-int", [200, 300], [200, 300]),
    ("list-int-duplicates", [200, 200], [200]),
    ("list-str", ["200", "300"], [200, 300]),
    ("list-str-duplicates", ["200", "200"], [200]),
    (
        "list-str-separated-ranges",
        ["2xx", "4xx"],
        chain(range(200, 300), range(400, 500)),
    ),
    ("list-str-overlap", ["200", "2xx", "222"], range(200, 300)),
    ("list-mixed-exact", ["200", 300], [200, 300]),
    ("list-mixed-duplicates", ["200", 200], [200]),
]


@pytest.mark.parametrize(
    ["status_codes", "expected"],
    [
        pytest.param(status_codes, set(expected), id=name)
        for name, status_codes, expected in _CASES_DESCRIPTIONS
    ],
)
def test_valid_cases(
    status_codes: Union[int, str, Iterable[Union[int, str]]], expected: Set[int]
) -> None:
    checker = build_status_code_check(status_codes)
    matching = set(filter(checker, range(1000)))
    assert matching == expected


@pytest.mark.parametrize("status_codes", [-42, 1000, "-42", "1000", "4xy"])
def test_invalid(status_codes: Union[int, str, Iterable[Union[int, str]]]) -> None:
    with pytest.raises(
        ValueError,
        match=re.escape(r"Invalid status code (must match /^[0-9x]{3}$/): "),
    ):
        build_status_code_check(status_codes)
