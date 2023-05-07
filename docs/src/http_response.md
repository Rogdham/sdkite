# HTTP Response

## Attributes

The following attributes of the HTTP response can be used:

`status_code`

: The HTTP status code (e.g. `401`)

`reason`

: The HTTP reason phrase (e.g. `"Unauthorized"`)

`headers`

: The HTTP headers as an `HTTPHeaderDict` instance

`data_bytes`

: The body of the response as `bytes`

`data_stream`

: The body of the response as an `Iterator[bytes]`; useful for streaming

`data_str`

: The body of the response as a `str`

`data_json`

: The body of the response JSON-decoded

`raw`

: The response object coming from the adapter (e.g. `requests.Response`)

## Usage as a context manager

Using a response as a context manager has two main effects.

First, some allocated resources are cleaned when leaving the context manager.

!!! Note

    This depends on the [HTTP engine](http_engine.md), but for example
    [requests](https://github.com/psf/requests) needs this in streaming mode to be able
    to release connections back to the pool.

Second, all exceptions raised within the context manager are caught an
`HTTPContextError` exception is raised instead.

    :::python
    >>> from sdkite.http import HTTPAdapterSpec, HTTPContextError

    >>> class RootClient(Client):
    ...     _http = HTTPAdapterSpec(url="https://api.example.com/")
    ...
    ...     def get_user(self, user_id):
    ...         with self._http.get(f"user/{user_id}") as response:
    ...             return (response.data_json["name"], response.data_json["age"])

    >>> RootClient().get_user(1)
    ('Alice', 42)

    >>> RootClient().get_user(2)
    Traceback (most recent call last):
        ...
    sdkite.http.exceptions.HTTPContextError: KeyError: 'age'

This is useful to have the HTTP context (request, response) in which the issue happened,
for example when validating the data returned by the API endpoint.

    :::python
    >>> try:
    ...     RootClient().get_user(2)
    ... except HTTPContextError as ex:
    ...     print(f"Invalid API response in URL {ex.request.url}")
    ...     print(f"Got JSON {ex.response.data_json}")
    ...     print(f"Exception raised is {ex}")
    Invalid API response in URL https://api.example.com/user/2
    Got JSON {'name': 'Bob'}
    Exception raised is KeyError: 'age'

!!! Note

    The original exception is available through the `__cause__` attribute of the
    `HTTPContextError` instance.
