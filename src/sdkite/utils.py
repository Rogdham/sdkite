import sys
from typing import Tuple, TypeVar

if sys.version_info < (3, 9):  # pragma: no cover
    from typing import Iterable, Sequence
else:  # pragma: no cover
    from collections.abc import Iterable, Sequence


T = TypeVar("T")
U = TypeVar("U")


def zip_reverse(items_a: Sequence[T], items_b: Sequence[U]) -> Iterable[Tuple[T, U]]:
    if len(items_a) != len(items_b):
        # in Python >= 3.10 we could use zip(..., strict=True)
        # but since we have sequences anyways this avoids dealing with backward compatibility
        raise ValueError("zip_reverse() arguments have different lengths")
    return zip(reversed(items_a), reversed(items_b))
