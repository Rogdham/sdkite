from abc import ABC, abstractmethod
from base64 import b64encode
from copy import deepcopy
import sys
from typing import Any, cast

from sdkite.http.adapter import HTTPAdapter, HTTPAdapterSpec
from sdkite.http.model import HTTPRequest

if sys.version_info < (3, 11):  # pragma: no cover
    from typing_extensions import Self
else:  # pragma: no cover
    from typing import Self


class Auth(ABC):
    name: str

    def __init__(
        self,
        http_adapter_spec: HTTPAdapterSpec,
        *,
        interceptor_order: int = 0,
    ) -> None:
        self._http_adapter_spec = http_adapter_spec
        self._interceptor_order = interceptor_order

    def __set_name__(self, _: Any, name: str) -> None:
        self.name = name
        self._http_adapter_spec.register_interceptor(
            "request_interceptor", self.name, self._interceptor_order
        )

    def __get__(self, instance: Any, __: Any) -> Self:
        if instance is None:
            return self
        attr_name = f"_sdkite_auth_{self.name}"
        try:
            instance_auth = getattr(instance, attr_name)
        except AttributeError:
            instance_auth = deepcopy(self)
            setattr(instance, attr_name, instance_auth)
        return cast(Self, instance_auth)

    @abstractmethod
    def __call__(self, request: HTTPRequest, _: HTTPAdapter) -> HTTPRequest:
        ...


class BasicAuth(Auth):
    def __init__(
        self,
        http_adapter_spec: HTTPAdapterSpec,
        username: str = "",
        password: str = "",
        *,
        interceptor_order: int = 0,
    ) -> None:
        super().__init__(http_adapter_spec, interceptor_order=interceptor_order)
        self.username = username
        self.password = password

    def __call__(self, request: HTTPRequest, _: HTTPAdapter) -> HTTPRequest:
        # pylint: disable=line-too-long

        # UTF-8 encoding seems to be the de-facto standard in browsers
        # see e.g. https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication#character_encoding_of_http_authentication

        # pylint: enable=line-too-long

        credentials = b64encode(f"{self.username}:{self.password}".encode()).decode()
        request.headers["Authorization"] = f"Basic {credentials}"
        return request


class NoAuth(Auth):
    def __call__(self, request: HTTPRequest, _: HTTPAdapter) -> HTTPRequest:
        return request
