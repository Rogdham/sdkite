import re
import sys
from typing import List, Optional

import pytest

from sdkite.utils import identity, last_not_none, walk_exception_context, zip_reverse

if sys.version_info < (3, 11):  # pragma: no cover
    from typing_extensions import assert_type
else:  # pragma: no cover
    from typing import assert_type


def test_identity() -> None:
    assert identity(42) == 42
    obj = object()
    assert identity(obj) == obj


def test_zip_reverse() -> None:
    assert list(zip_reverse((1, 2), "ab")) == [(2, "b"), (1, "a")]


def test_zip_reverse_invalid_sizes() -> None:
    with pytest.raises(
        ValueError,
        match=re.escape("zip_reverse() arguments have different lengths"),
    ):
        zip_reverse((1, 2), "abc")


@pytest.mark.parametrize(
    ["items", "expected"],
    [
        pytest.param([], None, id="empty"),
        pytest.param([1], 1, id="mandatory-1"),
        pytest.param([1, 2, 3], 3, id="mandatory-3"),
        pytest.param([None, None, 1, 2, 3], 3, id="optional-before"),
        pytest.param([1, 2, 3, None, None], 3, id="optional-after"),
        pytest.param([None, 1, None, 2, None, 3, None], 3, id="optional-interleaved"),
    ],
)
def test_last_not_none(items: List[Optional[int]], expected: Optional[int]) -> None:
    assert last_not_none(items) == expected
    if expected is None:
        assert last_not_none(items, -42) == -42
    else:
        assert last_not_none(items, -42) == expected


def test_last_not_none_typing() -> None:
    mandatory_list: List[int] = []
    optional_list: List[Optional[int]] = []

    assert_type(last_not_none(mandatory_list), Optional[int])
    assert_type(last_not_none(mandatory_list, 42), int)
    assert_type(last_not_none(optional_list), Optional[int])
    assert_type(last_not_none(optional_list, 42), int)


@pytest.mark.parametrize("exception_cause", [None, True, False])
def test_walk_exception_context(exception_cause: Optional[bool]) -> None:
    class AException(BaseException):
        pass

    class BException(BaseException):
        pass

    class CException(BaseException):
        pass

    exception = None
    try:
        try:
            try:
                raise AException
            except AException as exa:
                raise BException from exa
        except BException as exb:
            if exception_cause is None:
                raise CException from None
            if exception_cause:
                raise CException from exb
            raise CException  # pylint: disable=raise-missing-from  # noqa: B904
    except CException as cex:
        exception = cex

    assert isinstance(exception, CException)

    assert isinstance(
        walk_exception_context(exception, ValueError),
        CException,
    )
    assert isinstance(
        walk_exception_context(exception, CException),
        BException,
    )
    assert isinstance(
        walk_exception_context(exception, (BException, CException)),
        AException,
    )
    assert (
        walk_exception_context(exception, (AException, BException, CException)) is None
    )
