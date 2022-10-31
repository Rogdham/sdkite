from typing import List, Optional

import pytest

from sdkite.http.utils import urljoin, urlsjoin


@pytest.mark.parametrize(
    "base, url, expected",
    [
        (None, None, None),
        ("", "", None),
        ("https://perdu.com", None, "https://perdu.com"),
        ("https://perdu.com/", None, "https://perdu.com/"),
        ("https://perdu.com", "", "https://perdu.com"),
        ("https://perdu.com/", "", "https://perdu.com/"),
        (None, "https://perdu.com", "https://perdu.com"),
        (None, "https://perdu.com/", "https://perdu.com/"),
        ("", "https://perdu.com", "https://perdu.com"),
        ("", "https://perdu.com/", "https://perdu.com/"),
        ("https://perdu.com", "https://perdu.org", "https://perdu.org"),
        ("https://perdu.com", "https://perdu.org/", "https://perdu.org/"),
        ("https://perdu.com/", "https://perdu.org", "https://perdu.org"),
        ("https://perdu.com/", "https://perdu.org/", "https://perdu.org/"),
        ("https://perdu.com", "abc/def", "https://perdu.com/abc/def"),
        ("https://perdu.com/", "abc/def", "https://perdu.com/abc/def"),
        ("https://perdu.com", "/abc/def", "https://perdu.com/abc/def"),
        ("https://perdu.com/", "/abc/def", "https://perdu.com/abc/def"),
        ("https://perdu.com/abc/def/ghi", "../jkl", "https://perdu.com/abc/def/jkl"),
        ("https://perdu.com/abc/def/ghi", "/jkl", "https://perdu.com/jkl"),
    ],
)
def test_urljoin(
    base: Optional[str], url: Optional[str], expected: Optional[str]
) -> None:
    assert urljoin(base, url) == expected


@pytest.mark.parametrize(
    "urls, expected",
    [
        (
            [],
            None,
        ),
        (
            [None, None, None],
            None,
        ),
        (
            ["https://example.com"],
            "https://example.com",
        ),
        (
            [None, "https://example.com"],
            "https://example.com",
        ),
        (
            ["https://example.com", None],
            "https://example.com",
        ),
        (
            [None, "https://example.com", None],
            "https://example.com",
        ),
        (
            ["https://example.com", "abc", "def"],
            "https://example.com/abc/def",
        ),
        (
            ["https://example.com/", "abc/", "def/"],
            "https://example.com/abc/def/",
        ),
        (
            ["https://example.com", "abc", "def", "../ghi"],
            "https://example.com/abc/ghi",
        ),
        (
            ["https://example.com", "abc", "def", "/ghi"],
            "https://example.com/ghi",
        ),
        (
            ["https://example.com", "abc", "def", "https://example.org/", "jkl"],
            "https://example.org/jkl",
        ),
    ],
)
def test_urlsjoin(urls: List[Optional[str]], expected: Optional[str]) -> None:
    assert urlsjoin(urls) == expected
