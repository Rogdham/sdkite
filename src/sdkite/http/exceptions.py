import sys
from typing import TYPE_CHECKING, Optional

from sdkite.exceptions import SDKiteError

if TYPE_CHECKING:  # pragma: no cover
    # avoid circular references
    from sdkite.http.model import HTTPRequest, HTTPResponse

if sys.version_info < (3, 11):  # pragma: no cover
    from typing_extensions import Self
else:  # pragma: no cover
    from typing import Self


class HTTPError(SDKiteError):
    request: "HTTPRequest"
    response: Optional["HTTPResponse"]

    def __init__(
        self,
        *,
        msg: str = "N/A",
        request: "HTTPRequest",
        response: Optional["HTTPResponse"] = None,
    ) -> None:
        super().__init__(msg)
        self.request = request
        self.response = response

    @classmethod
    def from_exception(
        cls,
        exception: BaseException,
        *,
        request: "HTTPRequest",
        response: Optional["HTTPResponse"] = None,
    ) -> Self:
        return cls(
            msg=f"{exception.__class__.__name__}: {exception}",
            request=request,
            response=response,
        )


class HTTPConnectionError(HTTPError):
    pass


class HTTPTimeoutError(HTTPError):
    pass


class HTTPStatusCodeError(HTTPError):
    response: "HTTPResponse"

    def __init__(
        self,
        *,
        status_code: int,
        request: "HTTPRequest",
        response: Optional["HTTPResponse"],
    ) -> None:
        super().__init__(
            msg=f"Unexpected status code: {status_code}",
            request=request,
            response=response,
        )
        self.status_code = status_code


class HTTPContextError(HTTPError):
    response: "HTTPResponse"

    def __init__(
        self,
        *,
        msg: str = "N/A",
        request: "HTTPRequest",
        response: "HTTPResponse",
    ) -> None:
        super().__init__(msg=msg, request=request, response=response)
