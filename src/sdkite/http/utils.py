from functools import reduce
import json
import sys
from typing import Optional, Tuple, Union
from urllib.parse import urljoin as _urljoin

from sdkite.http.model import HTTPBodyEncoding

if sys.version_info < (3, 9):  # pragma: no cover
    from typing import Iterable, Iterator
else:  # pragma: no cover
    from collections.abc import Iterable, Iterator


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


def encode_request_body(
    body: object,
    encoding: HTTPBodyEncoding,
) -> Tuple[Union[bytes, Iterator[bytes]], Optional[str]]:
    type_error = TypeError(
        f"Cannot encode '{type(body).__name__}' body with '{encoding.name}' encoding"
    )

    # empty body
    if body is None:
        if encoding in (HTTPBodyEncoding.AUTO, HTTPBodyEncoding.NONE):
            return (b"", None)
        if encoding == HTTPBodyEncoding.JSON:
            return (b"null", "application/json")
        raise type_error

    # bytes
    if isinstance(body, bytes):
        if encoding in (HTTPBodyEncoding.AUTO, HTTPBodyEncoding.NONE):
            return (body, None)
        raise type_error

    # str
    if isinstance(body, str):
        if encoding in (HTTPBodyEncoding.AUTO, HTTPBodyEncoding.NONE):
            return (body.encode(), None)
        if encoding == HTTPBodyEncoding.JSON:
            return (json.dumps(body).encode(), "application/json")
        raise type_error

    # complex types
    raise NotImplementedError(
        "Encoding of complex body types is not supported yet"
    )  # pragma: no cover
