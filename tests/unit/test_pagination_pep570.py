# this file requires Python 3.8

from inspect import Parameter, signature
import sys
from typing import TYPE_CHECKING, Any, List, Protocol, get_type_hints

from sdkite import Pagination, paginated

if sys.version_info < (3, 9):  # pragma: no cover
    from typing import Iterator
else:  # pragma: no cover
    from collections.abc import Iterator


if TYPE_CHECKING:
    from typing_extensions import assert_type
else:
    # no need to have typing_extensions installed
    def assert_type(val: Any, _: Any) -> Any:
        return val


# this file uses positional-only parameters (PEP 570)
# which is only supported from Python 3.8

# this needs to be merged with regular test file
# when support for Python 3.7 is dropped


def test_paginated_wrapping_function_pep570() -> None:
    @paginated()
    def fct(
        pagination: Pagination,
        var_a: int,
        /,
        var_b: int,
        *var_c: int,
        var_d: int,
        var_e: int = 42,
        **var_f: int,
    ) -> List[int]:
        """Foobar"""
        if pagination.page == 0:
            return [var_a, var_b, *var_c, var_d, var_e, *var_f.values()]
        return []

    class ExpectedType(Protocol):
        def __call__(
            self,
            var_a: int,
            /,
            var_b: int,
            *var_c: int,
            var_d: int,
            var_e: int = 42,
            **var_f: int,
        ) -> Iterator[int]:
            ...

    assert_type(fct, ExpectedType)

    assert fct.__name__ == "fct", "name"
    assert fct.__doc__ == "Foobar", "doc"
    sig = signature(fct)
    assert list(sig.parameters.values()) == [
        Parameter("var_a", Parameter.POSITIONAL_ONLY, annotation=int),
        Parameter("var_b", Parameter.POSITIONAL_OR_KEYWORD, annotation=int),
        Parameter("var_c", Parameter.VAR_POSITIONAL, annotation=int),
        Parameter("var_d", Parameter.KEYWORD_ONLY, annotation=int),
        Parameter("var_e", Parameter.KEYWORD_ONLY, annotation=int, default=42),
        Parameter("var_f", Parameter.VAR_KEYWORD, annotation=int),
    ], "signature parameters"
    assert sig.return_annotation == Iterator[Any], "signature return_annotation"
    assert get_type_hints(fct) == {
        "var_a": int,
        "var_b": int,
        "var_c": int,
        "var_d": int,
        "var_e": int,
        "var_f": int,
        "return": Iterator[Any],
    }

    assert list(fct(1, 2, 3, 4, foo=5, bar=6, var_d=7)) == [1, 2, 3, 4, 7, 42, 5, 6]


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

    class ExpectedClassMethodType(Protocol):
        def __call__(
            self,
            obj: Klass,
            /,
            var_a: int,
            *var_b: int,
            var_c: int,
            var_d: int = 42,
            **var_e: int,
        ) -> Iterator[int]:
            ...

    assert_type(Klass.meth, ExpectedClassMethodType)
