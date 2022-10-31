from binascii import crc32
from inspect import Parameter, signature
import sys
from typing import TYPE_CHECKING, Any, List, Optional, cast, get_type_hints
from unittest.mock import Mock, call

import pytest

from sdkite import Pagination, paginated

if sys.version_info < (3, 8):  # pragma: no cover
    from typing_extensions import Protocol
else:  # pragma: no cover
    from typing import Protocol

if sys.version_info < (3, 9):  # pragma: no cover
    from typing import Iterable, Iterator
else:  # pragma: no cover
    from collections.abc import Iterable, Iterator


if TYPE_CHECKING:
    from typing_extensions import assert_type
else:
    # no need to have typing_extensions installed
    def assert_type(val: Any, _: Any) -> Any:
        return val


def test_paginated_page() -> None:
    mock_range = Mock(side_effect=range)

    @paginated()
    def fct(pagination: Pagination) -> Iterable[int]:
        page_size = 20
        start = pagination.page * page_size
        stop = start + page_size
        if stop == 100:
            pagination.finish()
        return cast(range, mock_range(start, stop))

    assert list(fct()) == list(range(100))
    assert mock_range.call_args_list == [
        call(0, 20),
        call(20, 40),
        call(40, 60),
        call(60, 80),
        call(80, 100),
    ]


def test_paginated_offset() -> None:
    mock_range = Mock(side_effect=range)

    @paginated()
    def fct(pagination: Pagination) -> Iterable[int]:
        start = pagination.offset
        stop = start * 2 + 1
        if stop > 100:
            pagination.finish()
        return cast(range, mock_range(start, stop))

    assert list(fct()) == list(range(127))
    assert mock_range.call_args_list == [
        call(0, 1),
        call(1, 3),
        call(3, 7),
        call(7, 15),
        call(15, 31),
        call(31, 63),
        call(63, 127),
    ]


def test_paginated_context() -> None:
    @paginated(context=b"00000000")
    def fct(pagination: Pagination) -> Iterable[str]:
        pagination.context = crc32(pagination.context).to_bytes(4, "big")
        value = pagination.context.hex()
        yield value
        if value[0] == "0":
            pagination.finish()

    assert list(fct()) == [
        "c0088d03",
        "4e3ed71e",
        "400c5633",
        "e07be581",
        "1629ad8a",
        "756e02aa",
        "3bd941ec",
        "c4e87e14",
        "d4fca750",
        "be8100bc",
        "fec968a5",
        "d21ba58f",
        "131d3482",
        "cf8a06b5",
        "0e995f9f",
    ]


@pytest.mark.parametrize("stop_when_empty", (None, True, False))
def test_paginated_stop_when_empty(stop_when_empty: Optional[bool]) -> None:
    mock_range = Mock(side_effect=range)
    sizes = [30, 10, 20, 0, 40, 50]

    if stop_when_empty is None:
        decorator = paginated()
    else:
        decorator = paginated(stop_when_empty=stop_when_empty)

    @decorator
    def fct(pagination: Pagination) -> Iterable[int]:
        start = pagination.offset
        try:
            stop = start + sizes[pagination.page]
        except IndexError:
            pagination.finish()
            return []
        return cast(range, mock_range(start, stop))

    # contrary to 'paginated', 'decorator' is not in pylint's 'signature-mutators'
    # pylint: disable-next=no-value-for-parameter
    return_value = fct()

    if stop_when_empty is False:
        assert list(return_value) == list(range(150))
        assert mock_range.call_args_list == [
            call(0, 30),
            call(30, 40),
            call(40, 60),
            call(60, 60),
            call(60, 100),
            call(100, 150),
        ]
    else:
        assert list(return_value) == list(range(60))
        assert mock_range.call_args_list == [
            call(0, 30),
            call(30, 40),
            call(40, 60),
            call(60, 60),
        ]


def test_paginated_wrapping_function() -> None:
    @paginated()
    def fct(
        pagination: Pagination,
        var_a: int,
        *var_b: int,
        var_c: int,
        var_d: int = 42,
        **var_e: int,
    ) -> List[int]:
        """Foobar"""
        if pagination.page == 0:
            return [var_a, *var_b, var_c, var_d, *var_e.values()]
        return []

    class ExpectedType(Protocol):
        def __call__(
            self,
            var_a: int,
            *var_b: int,
            var_c: int,
            var_d: int = 42,
            **var_e: int,
        ) -> Iterator[int]:
            ...

    assert_type(fct, ExpectedType)

    assert fct.__name__ == "fct", "name"
    assert fct.__doc__ == "Foobar", "doc"
    sig = signature(fct)
    assert list(sig.parameters.values()) == [
        Parameter("var_a", Parameter.POSITIONAL_OR_KEYWORD, annotation=int),
        Parameter("var_b", Parameter.VAR_POSITIONAL, annotation=int),
        Parameter("var_c", Parameter.KEYWORD_ONLY, annotation=int),
        Parameter("var_d", Parameter.KEYWORD_ONLY, annotation=int, default=42),
        Parameter("var_e", Parameter.VAR_KEYWORD, annotation=int),
    ], "signature parameters"
    assert sig.return_annotation == Iterator[Any], "signature return_annotation"
    assert get_type_hints(fct) == {
        "var_a": int,
        "var_b": int,
        "var_c": int,
        "var_d": int,
        "var_e": int,
        "return": Iterator[Any],
    }

    assert list(fct(1, 2, 3, foo=4, bar=5, var_c=6)) == [1, 2, 3, 6, 42, 4, 5]


def test_paginated_wrapping_method() -> None:
    class Klass:
        def __init__(self, value: int) -> None:
            self.value = value

        @paginated()
        def meth(
            self,
            pagination: Pagination,
            var_a: int,
            *var_b: int,
            var_c: int,
            var_d: int = 42,
            **var_e: int,
        ) -> List[int]:
            """Foobar"""
            if pagination.page == 0:
                return [self.value, var_a, *var_b, var_c, var_d, *var_e.values()]
            return []

        # assert_type(Klass.meth, ...) performed other file test due to PEP 570 requirement

    assert Klass.meth.__name__ == "meth", "name"
    assert Klass.meth.__doc__ == "Foobar", "doc"
    sig = signature(Klass.meth)
    assert list(sig.parameters.values()) == [
        Parameter("self", Parameter.POSITIONAL_OR_KEYWORD),
        Parameter("var_a", Parameter.POSITIONAL_OR_KEYWORD, annotation=int),
        Parameter("var_b", Parameter.VAR_POSITIONAL, annotation=int),
        Parameter("var_c", Parameter.KEYWORD_ONLY, annotation=int),
        Parameter("var_d", Parameter.KEYWORD_ONLY, annotation=int, default=42),
        Parameter("var_e", Parameter.VAR_KEYWORD, annotation=int),
    ], "signature parameters"
    assert sig.return_annotation == Iterator[Any], "signature return_annotation"
    assert get_type_hints(Klass.meth) == {
        "var_a": int,
        "var_b": int,
        "var_c": int,
        "var_d": int,
        "var_e": int,
        "return": Iterator[Any],
    }

    instance = Klass(1337)

    class ExpectedType(Protocol):
        def __call__(
            self,
            var_a: int,
            *var_b: int,
            var_c: int,
            var_d: int = 42,
            **var_e: int,
        ) -> Iterator[int]:
            ...

    assert_type(instance.meth, ExpectedType)

    assert instance.meth.__name__ == "meth", "name"
    assert instance.meth.__doc__ == "Foobar", "doc"
    sig = signature(instance.meth)
    assert list(sig.parameters.values()) == [
        Parameter("var_a", Parameter.POSITIONAL_OR_KEYWORD, annotation=int),
        Parameter("var_b", Parameter.VAR_POSITIONAL, annotation=int),
        Parameter("var_c", Parameter.KEYWORD_ONLY, annotation=int),
        Parameter("var_d", Parameter.KEYWORD_ONLY, annotation=int, default=42),
        Parameter("var_e", Parameter.VAR_KEYWORD, annotation=int),
    ], "signature parameters"
    assert sig.return_annotation == Iterator[Any], "signature return_annotation"
    assert get_type_hints(instance.meth) == {
        "var_a": int,
        "var_b": int,
        "var_c": int,
        "var_d": int,
        "var_e": int,
        "return": Iterator[Any],
    }

    assert list(instance.meth(1, 2, 3, foo=4, bar=5, var_c=6)) == [
        1337,
        1,
        2,
        3,
        6,
        42,
        4,
        5,
    ]


def test_paginated_wrapping_staticmethod() -> None:
    class Klass:
        @staticmethod
        @paginated()
        def meth0(
            pagination: Pagination,
            var_a: int,
            *var_b: int,
            var_c: int,
            var_d: int = 42,
            **var_e: int,
        ) -> List[int]:
            """Foobar"""
            if pagination.page == 0:
                return [var_a, *var_b, var_c, var_d, *var_e.values()]
            return []

        @paginated()
        @staticmethod
        def meth1(
            pagination: Pagination,
            var_a: int,
            *var_b: int,
            var_c: int,
            var_d: int = 42,
            **var_e: int,
        ) -> List[int]:
            """Foobar"""
            if pagination.page == 0:
                return [var_a, *var_b, var_c, var_d, *var_e.values()]
            return []

    class ExpectedType(Protocol):
        def __call__(
            self,
            var_a: int,
            *var_b: int,
            var_c: int,
            var_d: int = 42,
            **var_e: int,
        ) -> Iterator[int]:
            ...

    instance = Klass()

    assert_type(Klass.meth0, ExpectedType)
    assert_type(Klass.meth1, ExpectedType)
    assert_type(instance.meth0, ExpectedType)
    assert_type(instance.meth1, ExpectedType)

    assert Klass.meth0.__name__ == "meth0", "name"
    assert Klass.meth1.__name__ == "meth1", "name"
    assert instance.meth0.__name__ == "meth0", "name"
    assert instance.meth1.__name__ == "meth1", "name"

    for meth in (Klass.meth0, Klass.meth1, instance.meth0, instance.meth1):
        assert meth.__doc__ == "Foobar", "doc"
        sig = signature(meth)
        assert list(sig.parameters.values()) == [
            Parameter("var_a", Parameter.POSITIONAL_OR_KEYWORD, annotation=int),
            Parameter("var_b", Parameter.VAR_POSITIONAL, annotation=int),
            Parameter("var_c", Parameter.KEYWORD_ONLY, annotation=int),
            Parameter("var_d", Parameter.KEYWORD_ONLY, annotation=int, default=42),
            Parameter("var_e", Parameter.VAR_KEYWORD, annotation=int),
        ], "signature parameters"
        assert sig.return_annotation == Iterator[Any], "signature return_annotation"
        assert get_type_hints(meth) == {
            "var_a": int,
            "var_b": int,
            "var_c": int,
            "var_d": int,
            "var_e": int,
            "return": Iterator[Any],
        }

        assert list(meth(1, 2, 3, foo=4, bar=5, var_c=6)) == [1, 2, 3, 6, 42, 4, 5]


def test_paginated_wrapping_classmethod() -> None:
    class Klass:
        value = 1337

        @classmethod
        @paginated()
        def meth0(
            cls,
            pagination: Pagination,
            var_a: int,
            *var_b: int,
            var_c: int,
            var_d: int = 42,
            **var_e: int,
        ) -> List[int]:
            """Foobar"""
            if pagination.page == 0:
                return [cls.value, var_a, *var_b, var_c, var_d, *var_e.values()]
            return []

        @paginated()
        @classmethod
        def meth1(
            cls,
            pagination: Pagination,
            var_a: int,
            *var_b: int,
            var_c: int,
            var_d: int = 42,
            **var_e: int,
        ) -> List[int]:
            """Foobar"""
            if pagination.page == 0:
                return [cls.value, var_a, *var_b, var_c, var_d, *var_e.values()]
            return []

    class ExpectedType(Protocol):
        def __call__(
            self,
            var_a: int,
            *var_b: int,
            var_c: int,
            var_d: int = 42,
            **var_e: int,
        ) -> Iterator[int]:
            ...

    assert_type(Klass.meth0, ExpectedType)
    assert_type(Klass.meth1, ExpectedType)

    assert Klass.meth0.__name__ == "meth0", "name"
    assert Klass.meth1.__name__ == "meth1", "name"

    for meth in (Klass.meth0, Klass.meth1):
        assert meth.__doc__ == "Foobar", "doc"
        sig = signature(meth)
        assert list(sig.parameters.values()) == [
            Parameter("var_a", Parameter.POSITIONAL_OR_KEYWORD, annotation=int),
            Parameter("var_b", Parameter.VAR_POSITIONAL, annotation=int),
            Parameter("var_c", Parameter.KEYWORD_ONLY, annotation=int),
            Parameter("var_d", Parameter.KEYWORD_ONLY, annotation=int, default=42),
            Parameter("var_e", Parameter.VAR_KEYWORD, annotation=int),
        ], "signature parameters"
        assert sig.return_annotation == Iterator[Any], "signature return_annotation"
        assert get_type_hints(meth) == {
            "var_a": int,
            "var_b": int,
            "var_c": int,
            "var_d": int,
            "var_e": int,
            "return": Iterator[Any],
        }

        assert list(meth(1, 2, 3, foo=4, bar=5, var_c=6)) == [
            1337,
            1,
            2,
            3,
            6,
            42,
            4,
            5,
        ]


def test_paginated_no_param() -> None:
    with pytest.raises(TypeError) as excinfo:

        @paginated()  # type: ignore[arg-type]
        def fct() -> Iterable[int]:
            yield 42

    assert (
        str(excinfo.value)
        == "Paginated function 'fct' must have 'pagination' as first parameter"
    )


def test_paginated_wrong_param_name() -> None:
    with pytest.raises(TypeError) as excinfo:

        @paginated()
        def fct(
            # pylint: disable=unused-argument
            param0: Pagination,
            param1: int,
        ) -> Iterable[int]:
            yield 42

    assert (
        str(excinfo.value)
        == "Paginated function 'fct' must have 'pagination' as first parameter"
    )


def test_paginated_wrong_param_kind() -> None:
    with pytest.raises(TypeError) as excinfo:

        @paginated()  # type: ignore[arg-type]
        def fct(
            # pylint: disable=unused-argument
            *,
            pagination: Pagination,
        ) -> Iterable[int]:
            yield 42

    assert (
        str(excinfo.value)
        == "Paginated function 'fct' must have 'pagination' as first parameter"
    )


def test_paginated_called_with_pagination_param() -> None:
    @paginated()
    def fct(
        # pylint: disable=unused-argument
        pagination: Pagination,
        *args: int,
        **kwargs: int,
    ) -> Iterable[int]:
        if pagination.page == 0:
            yield 42

    assert list(fct(13, param=37)) == [42]

    with pytest.raises(TypeError) as excinfo:
        list(fct(13, pagination=37))

    assert (
        str(excinfo.value)
        == "Paginated function 'fct' cannot be called with a 'pagination' parameter"
    )


def test_paginated_no_type_hint() -> None:
    @paginated()
    def fct(pagination):  # type: ignore
        if pagination.page == 4:
            pagination.finish()
        return range(pagination.offset, pagination.offset + 10)

    assert list(fct()) == list(range(50))
