from copy import deepcopy
from dataclasses import dataclass
from functools import partial
from inspect import BoundArguments, signature
import sys
from typing import Any, Dict, List, Optional, Set, Tuple, TypeVar, Union
import warnings

from tenacity import (
    RetryCallState,
    Retrying,
    stop_after_attempt,
    wait_exponential_jitter,
)

from sdkite import Adapter, AdapterSpec
from sdkite.http.engine_requests import HTTPEngineRequests
from sdkite.http.exceptions import HTTPStatusCodeError
from sdkite.http.model import (
    HTTPBodyEncoding,
    HTTPHeaderDict,
    HTTPRequest,
    HTTPRequestAttemptInfo,
    HTTPResponse,
)
from sdkite.http.utils import build_status_code_check, encode_request_body, urlsjoin
from sdkite.utils import last_not_none, zip_reverse

if sys.version_info < (3, 8):  # pragma: no cover
    from typing_extensions import Literal, Protocol
else:  # pragma: no cover
    from typing import Literal, Protocol

if sys.version_info < (3, 9):  # pragma: no cover
    from typing import Callable, Iterable, Mapping
else:  # pragma: no cover
    from collections.abc import Callable, Iterable, Mapping

if sys.version_info < (3, 10):  # pragma: no cover
    from typing_extensions import ParamSpec
else:  # pragma: no cover
    from typing import ParamSpec


P = ParamSpec("P")
T = TypeVar("T")

HTTPAdapterSendRequest = Callable[[HTTPRequest], HTTPResponse]


_DEFAULT_RETRY_NB_ATTEMPTS = 3
_DEFAULT_WAIT_INITIAL = 1.0
_DEFAULT_WAIT_MAX = 60.0
_DEFAULT_WAIT_JITTER = 1.0


class _HTTPAdapterRequestWithoutMethodReturn(Protocol):
    def __call__(
        self,
        url: Optional[str] = None,
        *,
        body: object = None,
        body_encoding: HTTPBodyEncoding = HTTPBodyEncoding.AUTO,
        headers: Optional[Mapping[str, str]] = None,
        stream_response: bool = False,
        expected_status_codes: Union[int, str, Iterable[Union[int, str]]] = 200,
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


@dataclass
class _BeforeSleep:
    retry_callback: Optional[Callable[[HTTPRequestAttemptInfo], None]]
    initial_request: HTTPRequest

    def __call__(self, retry_call_state: RetryCallState) -> None:
        if self.retry_callback is None:
            return
        exception: BaseException = (
            retry_call_state.outcome.exception()  # type: ignore[union-attr, assignment]
        )
        seconds_since_start: float = (
            retry_call_state.seconds_since_start  # type: ignore[assignment]
        )
        self.retry_callback(
            HTTPRequestAttemptInfo(
                attempt_number=retry_call_state.attempt_number,
                initial_request=self.initial_request,
                exception=exception,
                seconds_since_start=seconds_since_start,
            )
        )


class HTTPAdapter(Adapter):
    url: Optional[str]
    headers: HTTPHeaderDict

    retry_nb_attempts: Optional[int]
    retry_callback: Optional[Callable[[HTTPRequestAttemptInfo], None]]
    retry_wait_initial: Optional[float]
    retry_wait_max: Optional[float]
    retry_wait_jitter: Optional[float]

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
        expected_status_codes: Union[int, str, Iterable[Union[int, str]]] = 200,
        retry_nb_attempts: Optional[int] = None,
        retry_callback: Optional[Callable[[HTTPRequestAttemptInfo], None]] = None,
        retry_wait_initial: Optional[float] = None,
        retry_wait_max: Optional[float] = None,
        retry_wait_jitter: Optional[float] = None,
    ) -> HTTPResponse:
        check_status_code = build_status_code_check(expected_status_codes)

        #
        # create request
        #

        # method
        method = method.upper()

        # url
        url = urlsjoin(self._from_adapter_hierarchy("url", url))
        if url is None:
            raise ValueError("No URL provided")

        # headers
        _headers = headers
        headers = HTTPHeaderDict()
        for headers_part in self._from_adapter_hierarchy("headers", _headers):
            if headers_part:
                headers.update(headers_part)
        del _headers

        # body
        body, content_type = encode_request_body(body, body_encoding)
        if content_type:
            if "content-type" in headers:
                warnings.warn(
                    "The 'content-type' header is being overridden"
                    f" due to request body encoding {body_encoding}"
                    f" (from '{headers['content-type']}' to '{content_type}')",
                    UserWarning,
                    stacklevel=1,
                )
            headers["content-type"] = content_type

        # create request object
        initial_request = HTTPRequest(
            method=method,
            url=url,
            headers=headers,
            body=body,
            stream_response=stream_response,
        )

        #
        # send request
        #

        # get values from parent adapters if None, or use default
        retry_nb_attempts = last_not_none(
            self._from_adapter_hierarchy("retry_nb_attempts", retry_nb_attempts),
            _DEFAULT_RETRY_NB_ATTEMPTS,
        )
        retry_callback = last_not_none(
            self._from_adapter_hierarchy("retry_callback", retry_callback)
        )
        retry_wait_initial = last_not_none(
            self._from_adapter_hierarchy("retry_wait_initial", retry_wait_initial),
            _DEFAULT_WAIT_INITIAL,
        )
        retry_wait_max = last_not_none(
            self._from_adapter_hierarchy("retry_wait_max", retry_wait_max),
            _DEFAULT_WAIT_MAX,
        )
        retry_wait_jitter = last_not_none(
            self._from_adapter_hierarchy("retry_wait_jitter", retry_wait_jitter),
            _DEFAULT_WAIT_JITTER,
        )

        before_sleep = _BeforeSleep(retry_callback, initial_request)

        for attempt in Retrying(
            stop=stop_after_attempt(retry_nb_attempts),
            wait=wait_exponential_jitter(
                initial=retry_wait_initial,
                max=retry_wait_max,
                jitter=retry_wait_jitter,
            ),
            before_sleep=before_sleep,
            reraise=True,
        ):
            request = deepcopy(initial_request)
            with attempt:
                # request interceptors
                for interceptor in self._get_interceptors("request_interceptor"):
                    request = interceptor(request, self)

                # send request
                response = self._send_request(request)

                # response interceptors
                for interceptor in self._get_interceptors("response_interceptor"):
                    response = interceptor(response, self)

                # status code check
                if not check_status_code(response.status_code):
                    raise HTTPStatusCodeError(
                        status_code=response.status_code,
                        request=initial_request,
                        response=response,
                    )

        response._set_context(  # pylint: disable=protected-access)  # noqa: SLF001
            initial_request
        )
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
        *,
        headers: Optional[Mapping[str, str]] = None,
        retry_nb_attempts: Optional[int] = None,
        retry_callback: Optional[Callable[[HTTPRequestAttemptInfo], None]] = None,
        retry_wait_initial: Optional[float] = None,
        retry_wait_max: Optional[float] = None,
        retry_wait_jitter: Optional[float] = None,
    ) -> None:
        self.url = url
        self.headers = HTTPHeaderDict(headers)

        self.retry_nb_attempts = retry_nb_attempts
        self.retry_callback = retry_callback
        self.retry_wait_initial = retry_wait_initial
        self.retry_wait_max = retry_wait_max
        self.retry_wait_jitter = retry_wait_jitter

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
                UserWarning,
                stacklevel=1,
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
