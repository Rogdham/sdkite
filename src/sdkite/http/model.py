from abc import ABC, abstractmethod
from contextlib import suppress
from dataclasses import dataclass
from enum import Enum, auto, unique
import sys
from types import TracebackType
from typing import Dict, List, Optional, Tuple, Type, Union

from sdkite.http.exceptions import HTTPContextError

if sys.version_info < (3, 9):  # pragma: no cover
    from typing import Iterable, Iterator, Mapping, MutableMapping
else:  # pragma: no cover
    from collections.abc import Iterable, Iterator, Mapping, MutableMapping

if sys.version_info < (3, 11):  # pragma: no cover
    from typing_extensions import Self
else:  # pragma: no cover
    from typing import Self


class HTTPHeaderDict(MutableMapping[str, str]):
    __slots__ = ["_contents"]

    def __init__(
        self,
        items: Union[None, Mapping[str, str], Iterable[Tuple[str, str]]] = None,
    ) -> None:
        self._contents: Dict[str, List[str]] = {}
        if isinstance(items, Mapping):
            items = items.items()
        if items:
            for key, value in items:
                self.add(key, value)

    def __repr__(self) -> str:
        as_dict = {values[0]: values[1:] for values in self._contents.values()}
        return f"HTTPHeaderDict{as_dict!r}"

    def __iter__(self) -> Iterator[str]:
        for values in self._contents.values():
            yield values[0]

    def __len__(self) -> int:
        return len(self._contents)

    def __getitem__(self, key: str) -> str:
        try:
            return ", ".join(self._contents[key.lower()][1:])
        except KeyError:
            raise KeyError(key) from None

    def __setitem__(self, key: str, value: str) -> None:
        self._contents[key.lower()] = [key, value]

    def __delitem__(self, key: str) -> None:
        del self._contents[key.lower()]

    def add(self, key: str, value: str) -> None:
        try:
            self._contents[key.lower()].append(value)
        except KeyError:
            self[key] = value


@unique
class HTTPBodyEncoding(Enum):
    AUTO = auto()
    NONE = auto()
    JSON = auto()
    URLENCODE = auto()
    MULTIPART = auto()


@dataclass
class HTTPRequest:
    method: str
    url: str
    headers: HTTPHeaderDict
    body: Union[bytes, Iterator[bytes]]
    stream_response: bool


class HTTPResponse(ABC):
    __context: Optional[HTTPRequest] = None

    @property
    @abstractmethod
    def raw(self) -> object:
        """
        The response object coming from the adapter
        """

    @property
    @abstractmethod
    def status_code(self) -> int:
        """
        The HTTP status code (RFC 2616 section 6.1.1)
        """

    @property
    @abstractmethod
    def reason(self) -> str:
        """
        The HTTP reason phrase (RFC 2616 section 6.1.1)
        """

    @property
    @abstractmethod
    def headers(self) -> HTTPHeaderDict:
        """
        The HTTP headers as a HTTPHeaderDict instance
        """

    @property
    @abstractmethod
    def data_stream(self) -> Iterator[bytes]:
        """
        The body of the response as an iterator of bytes, useful for data streaming.
        """

    @property
    @abstractmethod
    def data_bytes(self) -> bytes:
        """
        The body of the response as bytes.
        """

    @property
    @abstractmethod
    def data_str(self) -> str:
        """
        The body of the response as a str, for easier access.
        """

    @property
    @abstractmethod
    def data_json(self) -> object:
        """
        The body of the response JSON-decoded, for easier access.
        """

    def _close(self) -> None:  # noqa: B027
        pass

    def _set_context(self, context: HTTPRequest) -> None:
        self.__context = context

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        with suppress(Exception):
            self._close()
        if exc_val and self.__context:
            raise HTTPContextError.from_exception(
                exc_val,
                request=self.__context,
                response=self,
            ) from exc_val

    def __del__(self) -> None:
        with suppress(Exception):
            self._close()


@dataclass
class HTTPRequestAttemptInfo:
    attempt_number: int
    exception: BaseException
    initial_request: HTTPRequest
    seconds_since_start: float
