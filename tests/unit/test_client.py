import pytest

from sdkite import Client


class ClientA(Client):
    pass


class ClientB(Client):
    xyz: ClientA
    uvw: ClientA


class ClientC(Client):
    var_a: int  # set in init
    var_b: int  # not set in init
    var_c: ClientA  # regular case
    var_d: "ClientA"  # quoted type
    var_e: ClientB  # recursive

    def __init__(self) -> None:
        super().__init__()
        self.var_a = 42


class ClientD(Client):
    xyz: ClientC


class ClientRec0(Client):
    xyz: "ClientRec1"


class ClientRec1(Client):
    uvw: ClientRec0


def test_no_subclients() -> None:
    client = ClientA()
    assert isinstance(client, ClientA)


def test_subclients() -> None:
    client = ClientC()

    assert client.var_a == 42
    with pytest.raises(AttributeError):
        client.var_b  # pylint: disable=pointless-statement
    assert isinstance(client, ClientC)

    assert isinstance(client.var_c, ClientA)
    assert isinstance(client.var_d, ClientA)
    assert isinstance(client.var_e, ClientB)

    assert isinstance(client.var_e.xyz, ClientA)
    assert isinstance(client.var_e.uvw, ClientA)

    assert client.var_c != client.var_d
    assert client.var_e.xyz != client.var_e.uvw
    assert client.var_e.xyz != client.var_c

    # pylint: disable=protected-access
    assert client._parent is None
    assert client.var_c._parent == client
    assert client.var_d._parent == client
    assert client.var_e._parent == client
    assert client.var_e.xyz._parent == client.var_e
    assert client.var_e.uvw._parent == client.var_e


def test_subclient_custom_init() -> None:
    with pytest.raises(TypeError):
        ClientD()


def test_subclients_recursive() -> None:
    with pytest.raises(TypeError):
        ClientRec0()

    with pytest.raises(TypeError):
        ClientRec1()
