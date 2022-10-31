from typing import TYPE_CHECKING, Any, List, cast

import pytest

from sdkite import Adapter, AdapterSpec

if TYPE_CHECKING:
    from sdkite import Client
else:
    # we want independent unit tests
    Client = object


class AdapterSimple:
    no_instance = True

    def __init__(self) -> None:
        assert AdapterSimple.no_instance
        AdapterSimple.no_instance = False


class AdapterSpecSimple(AdapterSpec[AdapterSimple]):
    def _create_adapter(self) -> AdapterSimple:
        return AdapterSimple()


class ClientSimple0(Client):
    _parent: Any = None
    adp = AdapterSpecSimple()


class ClientSimple1(Client):
    _parent: Any = None
    adp = AdapterSpecSimple()


@pytest.mark.parametrize("swap_order", [False, True])
def test_adapter_spec_simple(swap_order: bool) -> None:
    AdapterSimple.no_instance = True

    assert isinstance(ClientSimple0.adp, AdapterSpecSimple)
    assert isinstance(ClientSimple1.adp, AdapterSpecSimple)

    client0 = ClientSimple0()
    client1 = ClientSimple1()
    client1._parent = client0  # pylint: disable=protected-access

    # different order of adp instantiation
    if swap_order:
        client1.adp  # pylint: disable=pointless-statement
        client0.adp  # pylint: disable=pointless-statement
    else:
        client0.adp  # pylint: disable=pointless-statement
        client1.adp  # pylint: disable=pointless-statement

    assert isinstance(client0.adp, AdapterSimple)
    assert isinstance(client1.adp, AdapterSimple)
    assert client0.adp is client1.adp


class AdapterComplex(Adapter):
    """A complex adapter"""

    uvw: List[int]
    xyz: List[str]

    no_instance = True

    def __init__(self) -> None:
        assert AdapterComplex.no_instance
        AdapterComplex.no_instance = False
        self.var = True

    def get_attr_name(self) -> str:
        return self._attr_name

    def get_client_names(self) -> List[str]:
        return [client.__class__.__name__ for client in self._clients]

    def get_adp_attrs(self) -> List[List[str]]:
        assert self._adapters[-1] == self
        return [adp.xyz for adp in self._adapters]

    def __repr__(self) -> str:
        return f"AC<{self.uvw},{self.xyz}>"


class AdapterSpecComplex(AdapterSpec[AdapterComplex]):
    uvw = [42]

    def __init__(self, *xyz: str) -> None:
        self.xyz = list(xyz)

    def _create_adapter(self) -> AdapterComplex:
        return AdapterComplex()


class ClientComplex0(Client):
    _parent: Any = None
    adp = AdapterSpecComplex("13", "37")


class ClientComplex1(Client):
    _parent: Any = None
    adp = AdapterSpecComplex("42")


@pytest.mark.parametrize("swap_order", [False, True])
def test_adapter_spec_complex(swap_order: bool) -> None:
    AdapterComplex.no_instance = True

    assert isinstance(ClientComplex0.adp, AdapterSpecComplex)
    assert isinstance(ClientComplex1.adp, AdapterSpecComplex)
    assert ClientComplex0.adp.uvw == [42]
    assert ClientComplex1.adp.uvw == [42]
    assert ClientComplex0.adp.xyz == ["13", "37"]
    assert ClientComplex1.adp.xyz == ["42"]

    client0 = ClientComplex0()
    client1 = ClientComplex1()
    client1._parent = client0  # pylint: disable=protected-access

    # different order of adp instantiation
    if swap_order:
        client1.adp  # pylint: disable=pointless-statement
        client0.adp  # pylint: disable=pointless-statement
    else:
        client0.adp  # pylint: disable=pointless-statement
        client1.adp  # pylint: disable=pointless-statement

    assert isinstance(client0.adp, AdapterComplex)
    assert isinstance(client1.adp, AdapterComplex)

    assert client0.adp.__doc__ == "A complex adapter"
    assert repr(client0.adp) == "AC<[42],['13', '37']>"

    assert client0.adp.uvw == [42]
    assert client1.adp.uvw == [42]
    assert client0.adp.xyz == ["13", "37"]
    assert client1.adp.xyz == ["42"]
    client0.adp.uvw.append(1337)
    client0.adp.xyz.append("end")
    assert client0.adp.uvw == [42, 1337]
    assert client1.adp.uvw == [42]  # not changed
    assert client0.adp.xyz == ["13", "37", "end"]
    assert client1.adp.xyz == ["42"]  # not changed

    AdapterComplex.no_instance = True
    client0bis = ClientComplex0()
    client1bis = ClientComplex1()
    client1bis._parent = client0bis  # pylint: disable=protected-access
    assert client0bis.adp.uvw == [42]  # not changed
    assert client1bis.adp.uvw == [42]  # not changed
    assert client0bis.adp.xyz == ["13", "37"]  # # not changed not changed
    assert client1bis.adp.xyz == ["42"]  # not changed

    assert client0.adp.var is True
    assert client1.adp.var is True
    client0.adp.var = False
    assert client0.adp.var is False
    assert cast(bool, client1.adp.var) is False  # changed

    assert client0.adp.get_attr_name() == "adp"
    assert client1.adp.get_attr_name() == "adp"
    assert client0.adp.get_client_names() == ["ClientComplex0"]
    assert client1.adp.get_client_names() == ["ClientComplex0", "ClientComplex1"]
    assert client0.adp.get_adp_attrs() == [["13", "37", "end"]]
    assert client1.adp.get_adp_attrs() == [["13", "37", "end"], ["42"]]

    assert client0bis.adp.get_adp_attrs() == [["13", "37"]]
    assert client1bis.adp.get_adp_attrs() == [["13", "37"], ["42"]]


class ClientNoAdapter(Client):
    _parent: Any = None


def test_client_middle_no_adapter() -> None:
    AdapterComplex.no_instance = True

    client0 = ClientComplex0()
    client1 = ClientNoAdapter()
    client1._parent = client0  # pylint: disable=protected-access
    client2 = ClientComplex1()
    client2._parent = client1  # pylint: disable=protected-access

    client0.adp  # pylint: disable=pointless-statement
    with pytest.raises(TypeError) as excinfo:
        client2.adp  # pylint: disable=pointless-statement

    assert str(excinfo.value) == "Client 'ClientComplex1' is missing adapter spec 'adp'"


class ClientMixed1(Client):
    _parent: Any = None
    adp = AdapterSpecComplex("37")


def test_client_various_adapters() -> None:
    AdapterSimple.no_instance = True
    AdapterComplex.no_instance = True

    client0 = ClientSimple0()
    client1 = ClientMixed1()
    client1._parent = client0  # pylint: disable=protected-access

    client0.adp  # pylint: disable=pointless-statement
    with pytest.raises(TypeError) as excinfo:
        client1.adp  # pylint: disable=pointless-statement

    assert str(excinfo.value) == (
        "Client 'ClientMixed1' has a wrong adapter spec: got 'AdapterSpecComplex' "
        "instead of 'AdapterSpecSimple'"
    )
