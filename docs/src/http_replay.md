# HTTP replay engine

Record and replay the HTTP interactions by setting the [HTTP engine](http_engine.md) to
`HTTPEngineReplay`. This is useful for fast and deterministic tests.

Inspired by [VCR](https://github.com/myronmarston/vcr) for Ruby and the similar projects
for Python.

!!! warning

    This feature is experimental, and the format in which records are saved on disk is subject to change in future versions.

## Engine parameters

`paths`

: An iterable of `Path`s to specify the record stores. If a request matches a record
from several paths, the last one will be used.

`recording` (optional)

: A `bool` telling wether real HTTP requests will be send (and saved) instead of loaded
from an existing record. Otherwise, no HTTP requests will be sent at all, and exceptions
will be raised if no matching requests are found in the record store.

`replay_request_modifier` (optional)

: Allow to modify the request before looking it up in the record store.

`replay_response_modifier` (optional)

: Allow to modify the response after retrieving it from the record store.

`recording_request_modifier` (optional)

: Allow to modify the request before sending the HTTP interaction for real. Only used in
recording mode. Note that the argument has not been modified by
`replay_request_modifier`.

`recording_response_modifier` (optional)

: Allow to modify the response received from a real HTTP interaction before saving it to
the record store. Only used in recording mode. Note that after being saved, the returned
value will then pass through `replay_response_modifier` before being sent to the caller.

`recording_compute_basename` (optional)

: Allow to compute the base name of the record file to be saved. A `.json` extension
will be appended to the returned value. Only used in recording mode.

## Example

    :::python
    >>> from sdkite import Client
    >>> from sdkite.http import HTTPAdapterSpec
    >>> from sdkite.http.engine_replay import HTTPEngineReplay

    >>> class TableTennis(Client):
    ...     _http = HTTPAdapterSpec("https://api.example.com/")
    ...
    ...     def ping(self):
    ...         return self._http.get("ping").data_str

    >>> TableTennis._http.set_engine(HTTPEngineReplay, [Path("replay")])

    >>> table_tennis = TableTennis()

    >>> table_tennis.ping()
    'pong'
