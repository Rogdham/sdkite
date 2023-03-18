import re

import pytest

from sdkite.http._stringescape import stringescape_loads


@pytest.mark.parametrize(
    ["data", "error_msg"],
    [
        pytest.param(r"abc\x0", r"Invalid data to load ('\\x0')", id="truncated"),
        pytest.param(
            r"abc\u0123456789", r"Invalid data to load ('\\u01')", id="invalid-escape"
        ),
        pytest.param(
            "in the æther", "Invalid data to load (not ascii)", id="non-ascii"
        ),
    ],
)
def test_stringescape_loads_invalid(data: str, error_msg: str) -> None:
    with pytest.raises(ValueError, match=re.escape(error_msg)):
        stringescape_loads(data)
