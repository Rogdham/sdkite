from contextlib import contextmanager
from functools import reduce
import json
import re
import secrets
import sys
from typing import Optional, Set, Tuple, Union
from urllib.parse import quote_plus
from urllib.parse import urljoin as _urljoin

from sdkite.http.model import HTTPBodyEncoding

if sys.version_info < (3, 9):  # pragma: no cover
    from typing import Callable, Iterable, Iterator
else:  # pragma: no cover
    from collections.abc import Callable, Iterable, Iterator

if sys.version_info < (3, 10):  # pragma: no cover
    NoneType = type(None)
else:  # pragma: no cover
    from types import NoneType


def urljoin(base: Optional[str], url: Optional[str]) -> Optional[str]:
    """
    Re-implementation of urljoin with some edge cases:
     - Handling of None values (note: this was the case with stdlib but undocumented)
     - Work more like os.path.join when base does not end with "/"
       e.g. __urljoin("https://example.com/foo", "bar")
            gives "https://example.com/foo/bar"
            and not "https://example.com/bar"
    """
    if base:
        if url:
            if not base.endswith("/"):
                base += "/"
            url = _urljoin(base, url)
        else:
            url = base
    elif not url:
        url = None
    return url


def urlsjoin(parts: Iterable[Optional[str]]) -> Optional[str]:
    return reduce(urljoin, parts, None)


def urlencode(data: Union[str, bytes]) -> bytes:
    return quote_plus(data).encode()


_EMPTY_ITERATOR = iter(())


class _VisitorTypeError(TypeError):
    def __init__(self, *path: str, obj: object) -> None:
        self.path = path
        self.obj = obj

    def context(self, path: str) -> "_VisitorTypeError":
        return _VisitorTypeError(path, *self.path, obj=self.obj)

    # the path item to use when the error happens in a mapping key
    MAPPING_KEY_PATH = ":key"


@contextmanager
def _visitor_obj(path: str, obj: object) -> Iterator[None]:
    try:
        yield
    except _VisitorTypeError as ex:
        raise ex.context(path) from None
    except TypeError:
        raise _VisitorTypeError(path, obj=obj) from None


class _Visitor:
    def visit(self, obj: object) -> Iterator[bytes]:
        try:
            for klass in (NoneType, str, bytes, bool, int, float):
                if isinstance(obj, klass):
                    yield from self._visit_raw(obj)
                    return
            if isinstance(obj, (list, tuple, set)):
                yield from self._visit_sequence_start()
                first = True
                for i, value in enumerate(sorted(obj) if isinstance(obj, set) else obj):
                    with _visitor_obj(repr(i), obj=value):
                        yield from self._visit_sequence_item_start(first=first)
                        yield from self.visit(value)
                        yield from self._visit_sequence_item_end(first=first)
                    first = False
                yield from self._visit_sequence_end()
                return
            if isinstance(obj, dict):
                yield from self._visit_mapping_start()
                first = True
                for key in sorted(obj):
                    with _visitor_obj(repr(key), obj=obj[key]):
                        yield from self._visit_mapping_item_start(key, first=first)
                        yield from self.visit(obj[key])
                        yield from self._visit_mapping_item_end(key, first=first)
                    first = False
                yield from self._visit_mapping_end()
                return
            raise TypeError
        except _VisitorTypeError:
            raise
        except TypeError:
            raise _VisitorTypeError(obj=obj) from None

    # pylint: disable=unused-argument

    def _visit_raw(self, obj: object) -> Iterator[bytes]:  # noqa: ARG002
        return _EMPTY_ITERATOR  # pragma: no cover

    def _visit_sequence_start(self) -> Iterator[bytes]:
        return _EMPTY_ITERATOR  # pragma: no cover

    def _visit_sequence_end(self) -> Iterator[bytes]:
        return _EMPTY_ITERATOR  # pragma: no cover

    def _visit_sequence_item_start(
        self, *, first: bool  # noqa: ARG002
    ) -> Iterator[bytes]:
        return _EMPTY_ITERATOR  # pragma: no cover

    def _visit_sequence_item_end(
        self, *, first: bool  # noqa: ARG002
    ) -> Iterator[bytes]:
        return _EMPTY_ITERATOR  # pragma: no cover

    def _visit_mapping_start(self) -> Iterator[bytes]:
        return _EMPTY_ITERATOR  # pragma: no cover

    def _visit_mapping_end(self) -> Iterator[bytes]:
        return _EMPTY_ITERATOR  # pragma: no cover

    def _visit_mapping_item_start(
        self, key: object, *, first: bool  # noqa: ARG002
    ) -> Iterator[bytes]:
        return _EMPTY_ITERATOR  # pragma: no cover

    def _visit_mapping_item_end(
        self, key: object, *, first: bool  # noqa: ARG002
    ) -> Iterator[bytes]:
        return _EMPTY_ITERATOR  # pragma: no cover


class _VisitorNone(_Visitor):
    def _visit_raw(self, obj: object) -> Iterator[bytes]:
        if obj is None:
            return
        if isinstance(obj, bytes):
            yield obj
            return
        if isinstance(obj, str):
            yield obj.encode()
            return
        raise TypeError

    def _visit_sequence_start(self) -> Iterator[bytes]:
        raise TypeError

    def _visit_mapping_start(self) -> Iterator[bytes]:
        raise TypeError


class _VisitorJSON(_Visitor):
    def _visit_raw(self, obj: object) -> Iterator[bytes]:
        yield json.dumps(obj).encode()

    def _visit_sequence_start(self) -> Iterator[bytes]:
        yield b"["

    def _visit_sequence_end(self) -> Iterator[bytes]:
        yield b"]"

    def _visit_sequence_item_start(self, *, first: bool) -> Iterator[bytes]:
        if not first:
            yield b","

    def _visit_mapping_start(self) -> Iterator[bytes]:
        yield b"{"

    def _visit_mapping_end(self) -> Iterator[bytes]:
        yield b"}"

    def _visit_mapping_item_start(self, key: object, *, first: bool) -> Iterator[bytes]:
        if not first:
            yield b","
        with _visitor_obj(_VisitorTypeError.MAPPING_KEY_PATH, obj=key):
            yield from self._visit_raw(key)
        yield b":"


class _VisitorURLEncode(_Visitor):
    root = True

    def _visit_raw(self, obj: object) -> Iterator[bytes]:
        if obj is None:
            return
        if self.root:
            raise TypeError
        if isinstance(obj, (bytes, str)):
            yield urlencode(obj)
            return
        raise TypeError

    def _visit_sequence_start(self) -> Iterator[bytes]:
        raise TypeError

    def _visit_mapping_start(self) -> Iterator[bytes]:
        if not self.root:
            raise TypeError
        self.root = False
        return _EMPTY_ITERATOR

    def _visit_mapping_item_start(self, key: object, *, first: bool) -> Iterator[bytes]:
        if not first:
            yield b"&"
        with _visitor_obj(_VisitorTypeError.MAPPING_KEY_PATH, obj=key):
            yield from self._visit_raw(key)
        yield b"="


class _VisitorMultipart(_Visitor):
    root = True

    def __init__(self) -> None:
        self.boundary = b"----%s" % secrets.token_hex(32).encode()

    def _visit_raw(self, obj: object) -> Iterator[bytes]:
        if self.root:
            raise TypeError
        if isinstance(obj, bytes):
            yield obj
            return
        if isinstance(obj, str):
            yield obj.encode()
            return
        raise TypeError

    def _visit_sequence_start(self) -> Iterator[bytes]:
        raise TypeError

    def _visit_mapping_start(self) -> Iterator[bytes]:
        if not self.root:
            raise TypeError
        self.root = False
        return _EMPTY_ITERATOR

    def _visit_mapping_item_start(
        self, key: object, *, first: bool  # noqa: ARG002
    ) -> Iterator[bytes]:
        with _visitor_obj(_VisitorTypeError.MAPPING_KEY_PATH, obj=key):
            name = b"".join(self._visit_raw(key))
        yield (
            b"--%s\r\n"
            b'Content-Disposition: form-data; name="%s"\r\n'
            b"Content-Type: application/octet-stream\r\n"
            b"\r\n"
        ) % (
            self.boundary,
            urlencode(name),
        )

    def _visit_mapping_item_end(
        self, key: object, *, first: bool  # noqa: ARG002
    ) -> Iterator[bytes]:
        yield b"\r\n"

    def _visit_mapping_end(self) -> Iterator[bytes]:
        yield b"--%s--\r\n" % self.boundary


def encode_request_body(
    body: object,
    encoding: HTTPBodyEncoding,
) -> Tuple[Union[bytes, Iterator[bytes]], Optional[str]]:
    content_type: Optional[str] = None
    original_encoding = encoding

    if encoding == HTTPBodyEncoding.AUTO:
        encoding = HTTPBodyEncoding.JSON
        if isinstance(body, (bytes, str, NoneType)):
            encoding = HTTPBodyEncoding.NONE
        elif isinstance(body, dict) and any(isinstance(key, bytes) for key in body):
            encoding = HTTPBodyEncoding.URLENCODE

    visitor: _Visitor
    if encoding == HTTPBodyEncoding.NONE:
        visitor = _VisitorNone()
    elif encoding == HTTPBodyEncoding.JSON:
        visitor = _VisitorJSON()
        content_type = "application/json"
    elif encoding == HTTPBodyEncoding.URLENCODE:
        visitor = _VisitorURLEncode()
        content_type = "application/x-www-form-urlencoded"
    elif encoding == HTTPBodyEncoding.MULTIPART:
        visitor = _VisitorMultipart()
        content_type = f"multipart/form-data; boundary={visitor.boundary.decode()}"
    else:
        raise TypeError("Invalid encoding type")

    try:
        iterator = visitor.visit(body)
        data = b"".join(iterator)
    except _VisitorTypeError as ex:
        error_msg = "Cannot encode body"
        if ex.path:
            error_msg += f" ({'>'.join(ex.path)})"
        error_msg += f" of type '{type(ex.obj).__name__}'"
        error_msg += f" with '{original_encoding.name}' encoding"
        raise TypeError(error_msg) from None

    return data, content_type


_SINGLE_STATUS_CODE_PATTERN = re.compile(r"^[0-9x]{3}$")


def build_status_code_check(
    status_codes: Union[int, str, Iterable[Union[int, str]]]
) -> Callable[[int], bool]:
    if isinstance(status_codes, (int, str)):
        status_codes = (status_codes,)

    parts: Set[str] = set()
    for status_code in status_codes:
        if isinstance(status_code, int):
            status_code = f"{status_code:03d}"  # noqa: PLW2901
        if _SINGLE_STATUS_CODE_PATTERN.match(status_code):
            parts.add(status_code.replace("x", "[0-9]"))
        else:
            raise ValueError(
                f"Invalid status code (must match /{_SINGLE_STATUS_CODE_PATTERN.pattern}/)"
                f": {status_code}"
            )

    pattern = re.compile(f"^{'|'.join(sorted(parts))}$")

    def status_code_check(code: int) -> bool:
        return bool(pattern.match(f"{code:03d}"))

    return status_code_check
