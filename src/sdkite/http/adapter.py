from functools import partial
from inspect import BoundArguments, signature
import sys
from typing import Any, Dict, List, Optional, Set, Tuple, TypeVar
import warnings

from sdkite import Adapter, AdapterSpec
from sdkite.http.engine_requests import HTTPEngineRequests
from sdkite.http.model import (
    HTTPBodyEncoding,
    HTTPHeaderDict,
    HTTPRequest,
    HTTPResponse,
)
from sdkite.http.utils import encode_request_body, urlsjoin
from sdkite.utils import zip_reverse

if sys.version_info < (3, 8):  # pragma: no cover
    from typing_extensions import Literal, Protocol
else:  # pragma: no cover
    from typing import Literal, Protocol

if sys.version_info < (3, 9):  # pragma: no cover
    from typing import Callable, Mapping
else:  # pragma: no cover
    from collections.abc import Callable, Mapping

if sys.version_info < (3, 10):  # pragma: no cover
    from typing_extensions import ParamSpec
else:  # pragma: no cover
    from typing import ParamSpec


P = ParamSpec("P")
T = TypeVar("T")

HTTPAdapterSendRequest = Callable[[HTTPRequest], HTTPResponse]


class _HTTPAdapterRequestWithoutMethodReturn(Protocol):
    def __call__(
        self,
        url: Optional[str] = None,
        *,
        body: object = None,
        body_encoding: HTTPBodyEncoding = HTTPBodyEncoding.AUTO,
        headers: Optional[Mapping[str, str]] = None,
        stream_response: bool = False,
    ) -> HTTPResponse:
        ...


class _HTTPAdapterRequestWithoutMethod:
    name: str

    def __set_name__(self, klass: Any, name: str) -> None:
        self.name = name

    def __get__(
        self, instance: "HTTPAdapter", klass: Any
    ) -> _HTTPAdapterRequestWithoutMethodReturn:
        return partial(instance.request, self.name)


class HTTPAdapter(Adapter):
    url: Optional[str]
    headers: HTTPHeaderDict
    request_interceptor: Dict[str, int]
    response_interceptor: Dict[str, int]

    def __init__(self, send_request: Callable[[HTTPRequest], HTTPResponse]) -> None:
        self._send_request = send_request

    get = _HTTPAdapterRequestWithoutMethod()
    options = _HTTPAdapterRequestWithoutMethod()
    head = _HTTPAdapterRequestWithoutMethod()
    post = _HTTPAdapterRequestWithoutMethod()
    put = _HTTPAdapterRequestWithoutMethod()
    patch = _HTTPAdapterRequestWithoutMethod()
    delete = _HTTPAdapterRequestWithoutMethod()

    def request(
        self,
        method: str,
        url: Optional[str] = None,
        *,
        body: object = None,
        body_encoding: HTTPBodyEncoding = HTTPBodyEncoding.AUTO,
        headers: Optional[Mapping[str, str]] = None,
        stream_response: bool = False,
    ) -> HTTPResponse:
        #
        # create request
        #

        # method
        method = method.upper()

        # url
        url_parts = [adapter.url for adapter in self._adapters]
        if url:
            url_parts.append(url)
        url = urlsjoin(url_parts)
        if url is None:
            raise ValueError("No URL provided")

        # headers
        headers_parts: List[Optional[Mapping[str, str]]] = [
            adapter.headers for adapter in self._adapters
        ]
        headers_parts.append(headers)
        headers = HTTPHeaderDict()
        for headers_part in headers_parts:
            if headers_part:
                headers.update(headers_part)

        # body
        body, content_type = encode_request_body(body, body_encoding)
        if content_type:
            if "content-type" in headers:
                warnings.warn(
                    "The 'content-type' header is being overridden"
                    f" due to request body encoding {body_encoding}"
                    f" (from '{headers['content-type']}' to '{content_type}')",
                    RuntimeWarning,
                )
            headers["content-type"] = content_type

        # create request object
        request = HTTPRequest(
            method=method,
            url=url,
            headers=headers,
            body=body,
            stream_response=stream_response,
        )

        #
        # send request
        #

        # request interceptors
        for interceptor in self._get_interceptors("request_interceptor"):
            request = interceptor(request, self)

        # send request
        response = self._send_request(request)

        # response interceptors
        for interceptor in self._get_interceptors("response_interceptor"):
            response = interceptor(response, self)

        return response

    def _get_interceptors(
        self,
        kind: Literal["request_interceptor", "response_interceptor"],
    ) -> List[Callable[[T, "HTTPAdapter"], T]]:
        seen_names: Set[str] = set()
        interceptors: List[Tuple[int, Callable[[T, HTTPAdapter], T]]] = []
        for client, adapter in zip_reverse(self._clients, self._adapters):
            for name, order in getattr(adapter, kind).items():
                if name not in seen_names:
                    interceptors.append((order, getattr(client, name)))
                    seen_names.add(name)
        interceptors.sort(key=lambda item: (item[0], str(item[1])))
        return [interceptor for _, interceptor in interceptors]


class HTTPAdapterSpec(AdapterSpec[HTTPAdapter]):
    _engine_callable: Callable[..., HTTPAdapterSendRequest]
    _engine_arguments: BoundArguments

    def __init__(
        self,
        url: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> None:
        self.url = url
        self.headers = HTTPHeaderDict(headers)
        self.request_interceptor: Dict[str, int] = {}
        self.response_interceptor: Dict[str, int] = {}

        # defaults to engine based on 'requests'
        self.set_engine(HTTPEngineRequests)

    def set_engine(
        self,
        engine_callable: Callable[P, HTTPAdapterSendRequest],
        *engine_args: P.args,
        **engine_kwargs: P.kwargs,
    ) -> None:
        arguments = signature(engine_callable).bind(*engine_args, **engine_kwargs)
        self._engine_callable = engine_callable
        self._engine_arguments = arguments

    def _create_adapter(self) -> HTTPAdapter:
        send_request = self._engine_callable(
            *self._engine_arguments.args,
            **self._engine_arguments.kwargs,
        )
        return HTTPAdapter(send_request)

    def register_interceptor(
        self,
        kind: Literal["request_interceptor", "response_interceptor"],
        attr_name: str,
        order: int,
    ) -> None:
        interceptors: Dict[str, int] = getattr(self, kind)
        if attr_name in interceptors:
            warnings.warn(
                f"Interceptor '{attr_name}' of '{self._attr_name}' has already been registered"
                f" with order {interceptors[attr_name]}, ignoring new registration"
                f" with order {order}",
                RuntimeWarning,
            )
        else:
            interceptors[attr_name] = order

    def _intercept(
        self,
        kind: Literal["request_interceptor", "response_interceptor"],
        order: int,
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        def decorator(fct: Callable[P, T]) -> Callable[P, T]:
            if sys.version_info < (3, 10):  # pragma: no cover
                if isinstance(fct, (classmethod, staticmethod)):
                    name = fct.__func__.__name__
                else:
                    name = fct.__name__
            else:  # pragma: no cover
                name = fct.__name__
            self.register_interceptor(kind, name, order)
            return fct

        return decorator

    def intercept_request(
        self, order: int
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        return self._intercept("request_interceptor", order)

    def intercept_response(
        self, order: int
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        return self._intercept("response_interceptor", order)
