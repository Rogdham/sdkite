from typing import Optional

import pytest

from sdkite.http import HTTPBodyEncoding
from sdkite.http.utils import encode_request_body


@pytest.mark.parametrize(
    "body, encoding, expected_is_iterator, expected_data, expected_content_type",
    [
        # None
        (None, HTTPBodyEncoding.AUTO, False, b"", None),
        (None, HTTPBodyEncoding.NONE, False, b"", None),
        (None, HTTPBodyEncoding.JSON, False, b"null", "application/json"),
        (None, HTTPBodyEncoding.URLENCODE, False, None, None),
        (None, HTTPBodyEncoding.MULTIPART, False, None, None),
        # bytes
        (b"abc", HTTPBodyEncoding.AUTO, False, b"abc", None),
        (b"abc", HTTPBodyEncoding.NONE, False, b"abc", None),
        (b"abc", HTTPBodyEncoding.JSON, False, None, None),
        (b"abc", HTTPBodyEncoding.URLENCODE, False, None, None),
        (b"abc", HTTPBodyEncoding.MULTIPART, False, None, None),
        # str
        ("æther", HTTPBodyEncoding.AUTO, False, b"\xc3\xa6ther", None),
        ("æther", HTTPBodyEncoding.NONE, False, b"\xc3\xa6ther", None),
        ("æther", HTTPBodyEncoding.JSON, False, b'"\\u00e6ther"', "application/json"),
        ("æther", HTTPBodyEncoding.URLENCODE, False, None, None),
        ("æther", HTTPBodyEncoding.MULTIPART, False, None, None),
    ],
)
def test_auto(
    body: object,
    encoding: HTTPBodyEncoding,
    expected_is_iterator: bool,
    expected_data: Optional[bytes],
    expected_content_type: Optional[str],
) -> None:
    if expected_data is None:
        with pytest.raises(TypeError):
            encode_request_body(body, encoding)
    else:
        data, content_type = encode_request_body(body, encoding)
        assert isinstance(data, bytes) != expected_is_iterator
        if isinstance(data, bytes):
            assert data == expected_data, "Invalid data"
        else:
            assert b"".join(data) == expected_data, "Invalid data"
        assert content_type == expected_content_type, "Invalid content type"
