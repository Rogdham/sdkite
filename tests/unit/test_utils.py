import pytest

from sdkite.utils import identity, zip_reverse


def test_identity() -> None:
    assert identity(42) == 42
    obj = object()
    assert identity(obj) == obj


def test_zip_reverse() -> None:
    assert list(zip_reverse((1, 2), "ab")) == [(2, "b"), (1, "a")]


def test_zip_reverse_invalid_sizes() -> None:
    with pytest.raises(ValueError):
        zip_reverse((1, 2), "abc")
