from typing import Dict, List

# not far from string-escape encoding in Python 2
# some differences include:
#  - encoding of single-quotes
#  - decoding of "invalid" escaped-sequences like `\z`

# see also: https://github.com/python/cpython/issues/74773

_dumps_table: Dict[int, str] = {}
_loads_table: Dict[bytes, int] = {}
for _i in range(256):
    _value = f"\\x{_i:02x}"
    _loads_table[_value.encode("ascii")] = _i
    if ord(" ") <= _i <= ord("~") and _i != ord("\\"):
        _value = chr(_i)
        _loads_table[_value.encode("ascii")] = _i
    _dumps_table[_i] = _value
for _i, _value in [
    (0, "\\0"),
    (9, "\\t"),
    (10, "\\n"),
    (13, "\\r"),
    (92, "\\\\"),
]:
    _dumps_table[_i] = _value
    _loads_table[_value.encode("ascii")] = _i
del _i, _value


def stringescape_loads(data: str) -> bytes:
    try:
        remaining = memoryview(data.encode("ascii"))
    except UnicodeEncodeError as ex:
        raise ValueError("Invalid data to load (not ascii)") from ex
    out: List[int] = []
    while remaining:
        for i in range(1, 5):
            part = remaining[:i].tobytes()
            try:
                out.append(_loads_table[part])
            except KeyError:
                pass
            else:
                remaining = remaining[i:]
                break
        else:
            raise ValueError(f"Invalid data to load ({part.decode('ascii')!r})")
    return bytes(out)


def stringescape_dumps(data: bytes) -> str:
    return "".join(_dumps_table[i] for i in data)
