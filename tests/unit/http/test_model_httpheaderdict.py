from typing import Dict, List, Tuple, Union

import pytest

from sdkite.http import HTTPHeaderDict

keys_cases = {
    "lower": "abc",
    "title": "Abc",
    "middle": "aBc",
    "upper": "ABC",
}


@pytest.mark.parametrize(
    "key", [pytest.param(key, id=name) for name, key in keys_cases.items()]
)
def test_getitem(key: str) -> None:
    value = "aBc01!$"
    hdict = HTTPHeaderDict()
    assert repr(hdict) == r"HTTPHeaderDict{}"

    for key2 in keys_cases.values():
        with pytest.raises(KeyError) as exc_info:
            hdict[key2]  # pylint: disable=pointless-statement
        assert exc_info.value.args == (key2,)

    hdict[key] = value
    assert repr(hdict) == f"HTTPHeaderDict{{'{key}': ['{value}']}}"

    for key2 in keys_cases.values():
        assert key2 in hdict
        assert hdict[key2] == value


def test_setitem() -> None:
    hdict = HTTPHeaderDict()
    assert "abc" not in hdict

    hdict["abc"] = "012"
    assert hdict["abc"] == "012"
    assert len(hdict) == 1
    assert dict(hdict) == {"abc": "012"}
    assert repr(hdict) == r"HTTPHeaderDict{'abc': ['012']}"

    hdict["abc"] = "345"
    assert hdict["abc"] == "345"
    assert len(hdict) == 1
    assert dict(hdict) == {"abc": "345"}
    assert repr(hdict) == r"HTTPHeaderDict{'abc': ['345']}"

    hdict["aBc"] = "678"
    assert hdict["abc"] == "678"
    assert len(hdict) == 1
    assert dict(hdict) == {"aBc": "678"}
    assert repr(hdict) == r"HTTPHeaderDict{'aBc': ['678']}"


def test_add() -> None:
    hdict = HTTPHeaderDict()
    assert "abc" not in hdict

    hdict.add("abc", "012")
    assert hdict["abc"] == "012"
    assert len(hdict) == 1
    assert dict(hdict) == {"abc": "012"}
    assert repr(hdict) == r"HTTPHeaderDict{'abc': ['012']}"

    hdict.add("abc", "345")
    assert hdict["abc"] == "012, 345"
    assert len(hdict) == 1
    assert dict(hdict) == {"abc": "012, 345"}
    assert repr(hdict) == r"HTTPHeaderDict{'abc': ['012', '345']}"

    hdict.add("aBc", "678")
    assert hdict["abc"] == "012, 345, 678"
    assert len(hdict) == 1
    assert dict(hdict) == {"abc": "012, 345, 678"}
    assert repr(hdict) == r"HTTPHeaderDict{'abc': ['012', '345', '678']}"


def test_add_keep_first_header_case() -> None:
    hdict = HTTPHeaderDict()
    assert "abc" not in hdict

    hdict.add("abC", "012")
    assert hdict["abc"] == "012"
    assert dict(hdict) == {"abC": "012"}
    assert repr(hdict) == r"HTTPHeaderDict{'abC': ['012']}"

    hdict.add("abc", "345")
    assert hdict["abc"] == "012, 345"
    assert dict(hdict) == {"abC": "012, 345"}
    assert repr(hdict) == r"HTTPHeaderDict{'abC': ['012', '345']}"

    hdict.add("aBc", "678")
    assert hdict["abc"] == "012, 345, 678"
    assert dict(hdict) == {"abC": "012, 345, 678"}
    assert repr(hdict) == r"HTTPHeaderDict{'abC': ['012', '345', '678']}"


def test_delitem() -> None:
    hdict = HTTPHeaderDict()
    hdict["aBc"] = "012"
    assert dict(hdict) == {"aBc": "012"}
    assert repr(hdict) == r"HTTPHeaderDict{'aBc': ['012']}"

    del hdict["abc"]

    for key in keys_cases.values():
        assert key not in hdict
    assert not dict(hdict)
    assert repr(hdict) == r"HTTPHeaderDict{}"

    hdict["abC"] = "345"
    assert dict(hdict) == {"abC": "345"}
    assert repr(hdict) == r"HTTPHeaderDict{'abC': ['345']}"


@pytest.mark.parametrize(
    "items",
    [
        None,
        {
            "aBc": "middle",
            "ABC": "upper",
            "XyZ": "012",
            "abc": "lower",
            "Abc": "title",
        },
        [
            ("aBc", "middle"),
            ("ABC", "upper"),
            ("XyZ", "012"),
            ("abc", "lower"),
            ("Abc", "title"),
        ],
    ],
    ids=type,
)
def test_init(items: Union[None, Dict[str, str], List[Tuple[str, str]]]) -> None:
    hdict = HTTPHeaderDict(items)
    if items is None:
        assert not dict(hdict)
        assert repr(hdict) == r"HTTPHeaderDict{}"
    else:
        assert dict(hdict) == {
            "aBc": "middle, upper, lower, title",
            "XyZ": "012",
        }
        assert repr(hdict) == (
            "HTTPHeaderDict{"
            "'aBc': ['middle', 'upper', 'lower', 'title'], "
            "'XyZ': ['012']}"
        )
