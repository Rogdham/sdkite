# HTTP engine

The HTTP engine is the responsible for taking an `HTTPRequest` and returning the
response as an `HTTPResponse` object.

The following engines are provided:

- `HTTPEngineRequests` based on the [requests](https://github.com/psf/requests); this
  engine is chosen by default
- `HTTPEngineReplay` to be able to record and replay requests
  ([more info](http_replay.md))

## Changing the engine

The method `HTTPAdapterSpec.set_engine` can be used to switch to an other engine:

    :::python
    >>> from sdkite import Client
    >>> from sdkite.http import HTTPAdapterSpec

    >>> class ExampleClient(Client):
    ...     _http = HTTPAdapterSpec("https://api.example.com/")
    ...     # directly when defining the Client class
    ...     _http.set_engine(ExampleEngine)

    # or afterwards
    >>> ExampleClient._http.set_engine(ExampleEngine)

    # but not once the client is instantiated!
    >>> client = ExampleClient()
    >>> client._http.set_engine(ExampleEngine)
    Traceback (most recent call last):
        ...
    AttributeError: 'HTTPAdapter' object has no attribute 'set_engine'

!!! Warning

    The engine must be set on the `HTTPAdapterSpec` of the root client, otherwise it is not used.

## Passing arguments to the engine

Arguments can be passed to the engine by providing them directly to `set_engine`.

    :::python
    >>> class ExampleClient(Client):
    ...     _http = HTTPAdapterSpec("https://api.example.com/")
    ...     _http.set_engine(ExampleEngine, 'pos0', 'pos1', kw0=13, kw1=37)
