# Quickstart

Let's write a SDK for an HTTP API that retrieves data from an imaginary world.

## Simple example

Let's start with an example:

    :::python
    >>> from sdkite import Client
    >>> from sdkite.http import HTTPAdapterSpec

    >>> class World(Client):
    ...     _http = HTTPAdapterSpec("https://api.example.com/world")
    ...
    ...     def npc_interact(self, name):
    ...         return self._http.get(f"npc/interact?name={name}").data_str
    ...
    ...     def npc_search(self, **kwargs):
    ...         return self._http.post(f"npc/search", body=kwargs).data_json

    >>> world = World()

    >>> world.npc_interact("ranis")
    'Have you found the Telvanni spy?'

    >>> world.npc_search(city="Balmora", faction="Mage", min_level=8)
    ['marayn', 'masalinie', 'ranis']

Notice thee following:

- Our root class `World` is a subclass of `Client`
- We have defined `_http` as a class variable
- The URLs parts `https://api.example.com/world` and `npc/info?name={name}` are combined
  to create the real URl that has been
  called: `https://api.example.com/world/npc/info?name=ranis`
- The `body` parameter is converted automatically to be used as the request body, but
  [a specific encoding can be specified](http_request.md)

!!! Note

    The `_http` naming is arbitrary; we suggest using a leading underscore `_` as
    [a convention][private-variables] to indicate to the consumer of the `World` class
    that the attribute should not be used directly.

[private-variables]: https://docs.python.org/3/tutorial/classes.html#private-variables

## More complex example

    :::python
    >>> from sdkite.http import BasicAuth

    >>> class WorldNpc(Client):
    ...     _http = HTTPAdapterSpec("npc")
    ...
    ...     def interact(self, name):
    ...         return self._http.get(f"interact?name={name}").data_str
    ...
    ...     def search(self, **kwargs):
    ...         return self._http.post(f"search", body=kwargs).data_json
    ...

    >>> class WorldBook(Client):
    ...     _http = HTTPAdapterSpec("book")
    ...
    ...     def download(self, book_id, path):
    ...         response = self._http.get(f"content?id={book_id}", stream_response=True)
    ...         with path.open("wb") as fp:
    ...             for data in response.data_stream:
    ...                 fp.write(data)

    >>> class World(Client):
    ...     _http = HTTPAdapterSpec("https://api.example.com/world")
    ...     _auth = BasicAuth(_http)
    ...
    ...     npc: WorldNpc
    ...     book: WorldBook
    ...
    ...     def __init__(self, username, password):
    ...         super().__init__()
    ...         self._auth.username = username
    ...         self._auth.password = password

    >>> world = World("Nerevarine", "Incarnate")

    >>> world.npc.interact("ranis")
    'Have you found the Telvanni spy?'

    >>> world.npc.interact("waldo")
    Traceback (most recent call last):
        ...
    sdkite.http.exceptions.HTTPStatusCodeError: Unexpected status code: 404

    >>> path = Path("book.txt")
    >>> world.book.download("bk_words_of_the_wind", path)
    >>> path.read_text()[:18]
    'Words of the Wind\n'

- Sub-clients are used to group endpoints together, and are automatically instantiated
- [Status codes are checked](http_request.md#expected-status-codes) and an exception is
  raised on missmatch (only `200` is allowed by default)
- [Basic authentication](http_auth.md) is set up on the root client, to be used on all
  sub-clients
- [Response streaming](http_request.md#stream-mode) is used to store the content of a
  book into a file
