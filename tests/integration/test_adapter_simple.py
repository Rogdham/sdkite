from io import SEEK_END, StringIO
from typing import TYPE_CHECKING, Any

from sdkite import AdapterSpec, Client

if TYPE_CHECKING:
    from typing_extensions import assert_type
else:
    # no need to have typing_extensions installed
    def assert_type(val: Any, _: Any) -> Any:
        return val


class ValueSpec(AdapterSpec[StringIO]):
    def _create_adapter(self) -> StringIO:
        return StringIO()  # not an Adapter instance


class ReadClient(Client):
    _value = ValueSpec()

    def normal(self) -> str:
        self._value.seek(0)
        return self._value.read()

    def upper(self) -> str:
        return self.normal().upper()


class WriteClient(Client):
    _value = ValueSpec()

    def erase(self) -> None:
        self._value.seek(0)
        self._value.truncate()

    def append(self, suffix: str) -> None:
        self._value.seek(0, SEEK_END)
        self._value.write(suffix)


class RootClient(Client):
    _value = ValueSpec()

    read: ReadClient
    write: WriteClient


def test_typing() -> None:
    client = RootClient()

    assert isinstance(assert_type(client, RootClient), RootClient)
    assert isinstance(assert_type(client.read, ReadClient), ReadClient)

    # pylint: disable=protected-access

    assert isinstance(assert_type(client._value, StringIO), StringIO)
    assert isinstance(assert_type(client.read._value, StringIO), StringIO)

    assert isinstance(assert_type(RootClient._value, ValueSpec), ValueSpec)


def test_complete() -> None:
    client = RootClient()
    assert client.read.normal() == ""
    assert client.read.upper() == ""

    client.write.append("Hello")
    assert client.read.normal() == "Hello"
    assert client.read.upper() == "HELLO"

    client.write.append(", world!")
    assert client.read.normal() == "Hello, world!"
    assert client.read.upper() == "HELLO, WORLD!"

    client.write.erase()
    assert client.read.normal() == ""
    assert client.read.upper() == ""


def test_two_clients() -> None:
    # two client instances are independent
    client0 = RootClient()
    client1 = RootClient()
    client0.write.append("Hello!")
    client1.write.append("How are you?")
    assert client0.read.normal() == "Hello!"
    assert client1.read.normal() == "How are you?"


class RootClientMissingValue(Client):
    read: ReadClient
    write: WriteClient


def test_root_client_missing_value() -> None:
    client = RootClientMissingValue()
    assert client.read.normal() == ""
    client.write.append("Hello")
    assert client.read.normal() == ""  # did not change
