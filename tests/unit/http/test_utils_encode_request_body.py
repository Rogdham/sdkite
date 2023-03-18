from dataclasses import dataclass
import re
import secrets
from typing import Dict, List, Optional, Tuple, Union

import pytest

from sdkite.http import HTTPBodyEncoding
from sdkite.http.utils import encode_request_body


@pytest.fixture(autouse=True)
def _patched_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(secrets, "token_hex", lambda size: "0" * size)


@dataclass
class Ok:
    data: Optional[bytes]
    content_type: Optional[str] = None
    is_iterator: bool = False


@dataclass
class Ko:
    err_type: str
    err_path: Optional[str] = None

    def msg(self, encoding: HTTPBodyEncoding) -> str:
        error_msg = "Cannot encode body"
        if self.err_path:
            error_msg += f" ({self.err_path})"
        error_msg += f" of type '{self.err_type}'"
        error_msg += f" with '{encoding.name}' encoding"
        return error_msg


class CustomClass:
    pass


CUSTOM_CLASS_INSTANCE = CustomClass()


# the type annotation makes sure deepest values are Ok or Ko instances
_CASES_DESCRIPTIONS: List[Tuple[str, object, Dict[HTTPBodyEncoding, Union[Ok, Ko]]]] = [
    (
        "None",
        None,
        {
            HTTPBodyEncoding.AUTO: Ok(b""),
            HTTPBodyEncoding.NONE: Ok(b""),
            HTTPBodyEncoding.JSON: Ok(b"null", "application/json"),
            HTTPBodyEncoding.URLENCODE: Ok(
                b"",
                "application/x-www-form-urlencoded",
            ),
            HTTPBodyEncoding.MULTIPART: Ko("NoneType"),
        },
    ),
    (
        "True",
        True,
        {
            HTTPBodyEncoding.AUTO: Ok(b"true", "application/json"),
            HTTPBodyEncoding.NONE: Ko("bool"),
            HTTPBodyEncoding.JSON: Ok(b"true", "application/json"),
            HTTPBodyEncoding.URLENCODE: Ko("bool"),
            HTTPBodyEncoding.MULTIPART: Ko("bool"),
        },
    ),
    (
        "False",
        False,
        {
            HTTPBodyEncoding.AUTO: Ok(b"false", "application/json"),
            HTTPBodyEncoding.NONE: Ko("bool"),
            HTTPBodyEncoding.JSON: Ok(b"false", "application/json"),
            HTTPBodyEncoding.URLENCODE: Ko("bool"),
            HTTPBodyEncoding.MULTIPART: Ko("bool"),
        },
    ),
    (
        "int",
        42,
        {
            HTTPBodyEncoding.AUTO: Ok(b"42", "application/json"),
            HTTPBodyEncoding.NONE: Ko("int"),
            HTTPBodyEncoding.JSON: Ok(b"42", "application/json"),
            HTTPBodyEncoding.URLENCODE: Ko("int"),
            HTTPBodyEncoding.MULTIPART: Ko("int"),
        },
    ),
    (
        "float",
        13.37,
        {
            HTTPBodyEncoding.AUTO: Ok(b"13.37", "application/json"),
            HTTPBodyEncoding.NONE: Ko("float"),
            HTTPBodyEncoding.JSON: Ok(b"13.37", "application/json"),
            HTTPBodyEncoding.URLENCODE: Ko("float"),
            HTTPBodyEncoding.MULTIPART: Ko("float"),
        },
    ),
    (
        "bytes",
        b"\xc3\xa6ther[1+2]%3",
        {
            HTTPBodyEncoding.AUTO: Ok(b"\xc3\xa6ther[1+2]%3"),
            HTTPBodyEncoding.NONE: Ok(b"\xc3\xa6ther[1+2]%3"),
            HTTPBodyEncoding.JSON: Ko("bytes"),
            HTTPBodyEncoding.URLENCODE: Ko("bytes"),
            HTTPBodyEncoding.MULTIPART: Ko("bytes"),
        },
    ),
    (
        "str",
        "æther[1+2]%3",
        {
            HTTPBodyEncoding.AUTO: Ok(b"\xc3\xa6ther[1+2]%3"),
            HTTPBodyEncoding.NONE: Ok(b"\xc3\xa6ther[1+2]%3"),
            HTTPBodyEncoding.JSON: Ok(b'"\\u00e6ther[1+2]%3"', "application/json"),
            HTTPBodyEncoding.URLENCODE: Ko("str"),
            HTTPBodyEncoding.MULTIPART: Ko("str"),
        },
    ),
    (
        "list[misc]",
        [42, True, b"foo", "bar"],
        {
            HTTPBodyEncoding.AUTO: Ko("bytes", "2"),
            HTTPBodyEncoding.NONE: Ko("list"),
            HTTPBodyEncoding.JSON: Ko("bytes", "2"),
            HTTPBodyEncoding.URLENCODE: Ko("list"),
            HTTPBodyEncoding.MULTIPART: Ko("list"),
        },
    ),
    (
        "list[str]",
        ["æther", "foo"],
        {
            HTTPBodyEncoding.AUTO: Ok(
                b'["\\u00e6ther","foo"]',
                "application/json",
            ),
            HTTPBodyEncoding.NONE: Ko("list"),
            HTTPBodyEncoding.JSON: Ok(
                b'["\\u00e6ther","foo"]',
                "application/json",
            ),
            HTTPBodyEncoding.URLENCODE: Ko("list"),
            HTTPBodyEncoding.MULTIPART: Ko("list"),
        },
    ),
    (
        "tuple[str]",
        ("æther", "foo"),
        {
            HTTPBodyEncoding.AUTO: Ok(
                b'["\\u00e6ther","foo"]',
                "application/json",
            ),
            HTTPBodyEncoding.NONE: Ko("tuple"),
            HTTPBodyEncoding.JSON: Ok(
                b'["\\u00e6ther","foo"]',
                "application/json",
            ),
            HTTPBodyEncoding.URLENCODE: Ko("tuple"),
            HTTPBodyEncoding.MULTIPART: Ko("tuple"),
        },
    ),
    (
        "set[str]",
        {"æther", "foo"},
        {
            HTTPBodyEncoding.AUTO: Ok(
                b'["foo","\\u00e6ther"]',
                "application/json",
            ),
            HTTPBodyEncoding.NONE: Ko("set"),
            HTTPBodyEncoding.JSON: Ok(
                b'["foo","\\u00e6ther"]',
                "application/json",
            ),
            HTTPBodyEncoding.URLENCODE: Ko("set"),
            HTTPBodyEncoding.MULTIPART: Ko("set"),
        },
    ),
    (
        "dict[bytes,bytes]",
        {b"\xc3\xa6ther": b"foobar", b"a[b=c]+%3": b"d[e=f]%+4"},
        {
            HTTPBodyEncoding.AUTO: Ok(
                b"a%5Bb%3Dc%5D%2B%253=d%5Be%3Df%5D%25%2B4&%C3%A6ther=foobar",
                "application/x-www-form-urlencoded",
            ),
            HTTPBodyEncoding.NONE: Ko("dict"),
            HTTPBodyEncoding.JSON: Ko("bytes", "b'a[b=c]+%3'>:key"),
            HTTPBodyEncoding.URLENCODE: Ok(
                b"a%5Bb%3Dc%5D%2B%253=d%5Be%3Df%5D%25%2B4&%C3%A6ther=foobar",
                "application/x-www-form-urlencoded",
            ),
            HTTPBodyEncoding.MULTIPART: Ok(
                (
                    b"------00000000000000000000000000000000\r\n"
                    b'Content-Disposition: form-data; name="a%5Bb%3Dc%5D%2B%253"\r\n'
                    b"Content-Type: application/octet-stream\r\n"
                    b"\r\n"
                    b"d[e=f]%+4"
                    b"\r\n"
                    b"------00000000000000000000000000000000\r\n"
                    b'Content-Disposition: form-data; name="%C3%A6ther"\r\n'
                    b"Content-Type: application/octet-stream\r\n"
                    b"\r\n"
                    b"foobar"
                    b"\r\n"
                    b"------00000000000000000000000000000000--\r\n"
                ),
                "multipart/form-data; boundary=----00000000000000000000000000000000",
            ),
        },
    ),
    (
        "dict[str,str]",
        {"æther": "foobar", "a[b=c]+%3": "d[e=f]%+4"},
        {
            HTTPBodyEncoding.AUTO: Ok(
                b'{"a[b=c]+%3":"d[e=f]%+4","\\u00e6ther":"foobar"}',
                "application/json",
            ),
            HTTPBodyEncoding.NONE: Ko("dict"),
            HTTPBodyEncoding.JSON: Ok(
                b'{"a[b=c]+%3":"d[e=f]%+4","\\u00e6ther":"foobar"}',
                "application/json",
            ),
            HTTPBodyEncoding.URLENCODE: Ok(
                b"a%5Bb%3Dc%5D%2B%253=d%5Be%3Df%5D%25%2B4&%C3%A6ther=foobar",
                "application/x-www-form-urlencoded",
            ),
            HTTPBodyEncoding.MULTIPART: Ok(
                (
                    b"------00000000000000000000000000000000\r\n"
                    b'Content-Disposition: form-data; name="a%5Bb%3Dc%5D%2B%253"\r\n'
                    b"Content-Type: application/octet-stream\r\n"
                    b"\r\n"
                    b"d[e=f]%+4"
                    b"\r\n"
                    b"------00000000000000000000000000000000\r\n"
                    b'Content-Disposition: form-data; name="%C3%A6ther"\r\n'
                    b"Content-Type: application/octet-stream\r\n"
                    b"\r\n"
                    b"foobar"
                    b"\r\n"
                    b"------00000000000000000000000000000000--\r\n"
                ),
                "multipart/form-data; boundary=----00000000000000000000000000000000",
            ),
        },
    ),
    (
        "dict[str,int]",
        {"uvw": 13, "xyz": 37},
        {
            HTTPBodyEncoding.AUTO: Ok(b'{"uvw":13,"xyz":37}', "application/json"),
            HTTPBodyEncoding.NONE: Ko("dict"),
            HTTPBodyEncoding.JSON: Ok(b'{"uvw":13,"xyz":37}', "application/json"),
            HTTPBodyEncoding.URLENCODE: Ko("int", "'uvw'"),
            HTTPBodyEncoding.MULTIPART: Ko("int", "'uvw'"),
        },
    ),
    (
        "dict[int,str]",
        {13: "37", 42: "42"},
        {
            HTTPBodyEncoding.AUTO: Ok(b'{13:"37",42:"42"}', "application/json"),
            HTTPBodyEncoding.NONE: Ko("dict"),
            HTTPBodyEncoding.JSON: Ok(b'{13:"37",42:"42"}', "application/json"),
            HTTPBodyEncoding.URLENCODE: Ko("int", "13>:key"),
            HTTPBodyEncoding.MULTIPART: Ko("int", "13>:key"),
        },
    ),
    (
        "dict[str,CustomClass]",
        {"xyz": CUSTOM_CLASS_INSTANCE},
        {
            HTTPBodyEncoding.AUTO: Ko("CustomClass", "'xyz'"),
            HTTPBodyEncoding.NONE: Ko("dict"),
            HTTPBodyEncoding.JSON: Ko("CustomClass", "'xyz'"),
            HTTPBodyEncoding.URLENCODE: Ko("CustomClass", "'xyz'"),
            HTTPBodyEncoding.MULTIPART: Ko("CustomClass", "'xyz'"),
        },
    ),
    (
        "dict[CustomClass,str]",
        {CUSTOM_CLASS_INSTANCE: "42"},
        {
            HTTPBodyEncoding.AUTO: Ko("CustomClass", f"{CUSTOM_CLASS_INSTANCE}>:key"),
            HTTPBodyEncoding.NONE: Ko("dict"),
            HTTPBodyEncoding.JSON: Ko("CustomClass", f"{CUSTOM_CLASS_INSTANCE}>:key"),
            HTTPBodyEncoding.URLENCODE: Ko(
                "CustomClass", f"{CUSTOM_CLASS_INSTANCE}>:key"
            ),
            HTTPBodyEncoding.MULTIPART: Ko(
                "CustomClass", f"{CUSTOM_CLASS_INSTANCE}>:key"
            ),
        },
    ),
    (
        "dict[str,dict[str,str]]",
        {"æther": "foobar", "abc": {"uvw": "xyz"}},
        {
            HTTPBodyEncoding.AUTO: Ok(
                b'{"abc":{"uvw":"xyz"},"\\u00e6ther":"foobar"}',
                "application/json",
            ),
            HTTPBodyEncoding.NONE: Ko("dict"),
            HTTPBodyEncoding.JSON: Ok(
                b'{"abc":{"uvw":"xyz"},"\\u00e6ther":"foobar"}',
                "application/json",
            ),
            HTTPBodyEncoding.URLENCODE: Ko("dict", "'abc'"),
            HTTPBodyEncoding.MULTIPART: Ko("dict", "'abc'"),
        },
    ),
    (
        "CustomClass",
        CUSTOM_CLASS_INSTANCE,
        {
            HTTPBodyEncoding.AUTO: Ko("CustomClass"),
            HTTPBodyEncoding.NONE: Ko("CustomClass"),
            HTTPBodyEncoding.JSON: Ko("CustomClass"),
            HTTPBodyEncoding.URLENCODE: Ko("CustomClass"),
            HTTPBodyEncoding.MULTIPART: Ko("CustomClass"),
        },
    ),
]


@pytest.mark.parametrize(
    ["body", "encoding", "expected"],
    [
        pytest.param(
            body,
            encoding,
            value,
            id=f"{encoding.name}-{name}",
        )
        for name, body, by_encoding in _CASES_DESCRIPTIONS
        for encoding, value in by_encoding.items()
    ],
)
def test_cases(
    body: object,
    encoding: HTTPBodyEncoding,
    expected: Union[Ok, Ko],
) -> None:
    if isinstance(expected, Ok):
        data, content_type = encode_request_body(body, encoding)
        assert isinstance(data, bytes) != expected.is_iterator
        if not isinstance(data, bytes):
            data = b"".join(data)
        assert data == expected.data, "Invalid data"
        assert content_type == expected.content_type, "Invalid content type"

    else:
        with pytest.raises(
            TypeError, match=re.escape(expected.msg(encoding))
        ) as excinfo:
            encode_request_body(body, encoding)

        assert excinfo.type is TypeError


def test_invalid_encoding_type() -> None:
    with pytest.raises(TypeError):
        encode_request_body(None, "oops")  # type: ignore[arg-type]
