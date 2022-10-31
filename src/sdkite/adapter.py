from abc import ABC, abstractmethod
from copy import deepcopy
import sys
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    get_type_hints,
    overload,
)

from sdkite.client import Client

A = TypeVar("A")


# until mypy has support for Self type
# see https://github.com/python/mypy/issues/11871
_AdapterSelf = TypeVar("_AdapterSelf", bound="Adapter")
_AdapterSpecSelf = TypeVar("_AdapterSpecSelf", bound="AdapterSpec[Any]")


class Adapter:
    _attr_name: str
    _clients: Tuple[Client, ...]

    @property
    def _adapters(self: _AdapterSelf) -> Tuple[_AdapterSelf, ...]:
        return tuple(getattr(client, self._attr_name) for client in self._clients)


def create_adapter_proxy(
    adapter: A,
    attr_name: str,
    clients: Tuple[Client, ...],
    context: Dict[str, Any],
) -> A:
    klass = type(adapter)

    # pylint: disable=unused-argument

    def init(self: Any) -> None:
        pass

    def getattribute(self: Any, name: str) -> Any:
        if name == "_attr_name":
            return attr_name
        if name == "_clients":
            return clients
        if name in context:
            return context[name]
        try:
            attr = super(type(self), self).__getattribute__(name)
        except AttributeError:
            attr = getattr(adapter, name)
        return attr

    def setattribute(self: Any, name: str, value: Any) -> None:
        if name in ("_attr_name", "_clients"):
            raise RuntimeError(f"Attribute {name} is read-only")  # pragma: no cover
        if name in context:
            context[name] = value
        else:
            setattr(adapter, name, value)

    return cast(
        A,
        type(
            f"{klass.__name__}*",
            (klass,),
            {
                "__init__": init,
                "__getattribute__": getattribute,
                "__setattr__": setattribute,
                "__doc__": getattr(klass, "__doc__", None),
            },
        )(),
    )


class AdapterSpec(Generic[A], ABC):
    _attr_name: str

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    def __set_name__(self, _: Any, name: str) -> None:
        self._attr_name = name

    @overload
    def __get__(self: _AdapterSpecSelf, client: None, _: Any) -> _AdapterSpecSelf:
        ...

    @overload
    def __get__(self, client: Client, _: Any) -> A:
        ...

    def __get__(
        self: _AdapterSpecSelf, client: Optional[Client], _: Any
    ) -> Union[_AdapterSpecSelf, A]:
        if client is None:
            return self

        _attr_name_adapter = f"_adapter__{self._attr_name}"
        _attr_name_adapter_real = f"_adapter_real__{self._attr_name}"

        # in cache
        adapter: Optional[A] = getattr(client, _attr_name_adapter, None)

        if adapter is None:
            # walk up clients chain
            current_client = client
            last_descriptor_type: Optional[Type[AdapterSpec[Any]]] = None
            clients: List[Client] = []
            expect_no_more_descriptors = False
            while True:
                try:
                    descriptor: AdapterSpec[A] = getattr(
                        type(current_client), self._attr_name
                    )
                except AttributeError:
                    expect_no_more_descriptors = True
                else:
                    if expect_no_more_descriptors:
                        raise TypeError(
                            f"Client '{type(clients[-1]).__name__}' is missing"
                            f" adapter spec '{self._attr_name}'"
                        )
                    if last_descriptor_type and (
                        # pylint: disable-next=unidiomatic-typecheck
                        type(descriptor)
                        is not last_descriptor_type
                    ):
                        raise TypeError(
                            f"Client '{type(clients[-1]).__name__}' has a wrong adapter spec:"
                            f" got '{last_descriptor_type.__name__}'"
                            f" instead of '{type(descriptor).__name__}'"
                        )
                    last_descriptor_type = type(descriptor)
                    clients.append(current_client)
                if current_client._parent:
                    current_client = current_client._parent
                else:
                    if sys.version_info < (3, 10):  # pragma: no cover
                        # fix coverage issue on some Python versions
                        # see https://github.com/nedbat/coveragepy/issues/1480
                        pass
                    break
            clients.reverse()
            root_client = clients[0]

            # create real adapter if needed
            try:
                real_adapter: A = getattr(root_client, _attr_name_adapter_real)
            except AttributeError:
                real_adapter = self._create_adapter()
                setattr(root_client, _attr_name_adapter_real, real_adapter)

            # create adapter proxy
            if isinstance(real_adapter, Adapter):
                adapter_proxy = create_adapter_proxy(
                    real_adapter,
                    self._attr_name,
                    tuple(clients),
                    {
                        attr_name: deepcopy(getattr(self, attr_name))
                        for attr_name in get_type_hints(real_adapter.__class__)
                        if not attr_name.startswith("_")
                    },
                )
                adapter = cast(A, adapter_proxy)
            else:
                adapter = real_adapter

            setattr(client, _attr_name_adapter, adapter)

        return adapter

    @abstractmethod
    def _create_adapter(self) -> A:
        ...
