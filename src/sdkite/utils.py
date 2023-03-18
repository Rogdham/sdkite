import sys
from typing import Optional, Tuple, Type, TypeVar, Union, overload

if sys.version_info < (3, 9):  # pragma: no cover
    from typing import Iterable, Reversible, Sequence
else:  # pragma: no cover
    from collections.abc import Iterable, Reversible, Sequence


T = TypeVar("T")
U = TypeVar("U")


def identity(value: T) -> T:
    return value


def zip_reverse(items_a: Sequence[T], items_b: Sequence[U]) -> Iterable[Tuple[T, U]]:
    if len(items_a) != len(items_b):
        # in Python >= 3.10 we could use zip(..., strict=True)
        # but since we have sequences anyways this avoids dealing with backward compatibility
        raise ValueError("zip_reverse() arguments have different lengths")
    return zip(reversed(items_a), reversed(items_b))


@overload
def last_not_none(items: Reversible[T]) -> Optional[T]:
    ...


@overload
def last_not_none(items: Reversible[Optional[T]], default: T) -> T:
    ...


def last_not_none(
    items: Reversible[Optional[T]], default: Optional[T] = None
) -> Optional[T]:
    for item in reversed(items):
        if item is not None:
            return item
    return default


def walk_exception_context(
    exception: Optional[BaseException],
    exclude_type: Union[Type[BaseException], Tuple[Type[BaseException], ...]],
) -> Optional[BaseException]:
    while exception is not None:
        if not isinstance(exception, exclude_type):
            return exception
        exception = exception.__context__
    return None
