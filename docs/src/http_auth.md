# HTTP authentication

Helpers are provided to manage the common schemes of HTTP authentications.

They take the `HTTPAdapterSpec` instance as first argument. Internally, they register an
interceptor <!-- FIXME link --> that will add the required `Authorization` header.

## Basic authentication

The `BasicAuth` helper takes to optional arguments `username` and `password`:

    :::python
    >>> from sdkite.http import BasicAuth, HTTPAdapterSpec

    >>> class RootClient(Client):
    ...     _http = HTTPAdapterSpec(url="https://api.example.com/")
    ...     _auth = BasicAuth(_http, "Alice", "W0nderl@nd")
    ...
    ...     def whoami(self):
    ...         return self._http.get('whoami').data_str

    >>> RootClient().whoami()
    'Welcome Alice!'

The values can also be set at runtime by modifying the corresponding attributes of the
instance:

    :::python
    >>> class RootClient(Client):
    ...     _http = HTTPAdapterSpec(url="https://api.example.com/")
    ...     _auth = BasicAuth(_http)
    ...
    ...     def __init__(self, username, password):
    ...         super().__init__()
    ...         self._auth.username = username
    ...         self._auth.password = password
    ...
    ...     def whoami(self):
    ...         return self._http.get('whoami').data_str

    >>> RootClient('Alice', 'W0nderl@nd').whoami()
    'Welcome Alice!'

## Removing authentication

If you have defined some authentication on a client, you can remove it on sub-clients by
using `NoAuth`:

    :::python
    >>> from sdkite.http import NoAuth

    >>> class ChildClient(Client):
    ...     _http = HTTPAdapterSpec()
    ...     _auth = NoAuth(_http)
    ...
    ...     def example(self):
    ...         return self._http.get('noauth').data_str

    >>> class RootClient(Client):
    ...     _http = HTTPAdapterSpec(url="https://api.example.com/")
    ...     _auth = BasicAuth(_http, "user", "password")
    ...     child: ChildClient

    >>> RootClient().child.example()  # will not add basic auth
    'The /noauth endpoint has been called without auth'

!!! Note

    The name of the class attribute (`_auth` in the example) must be the same in both clients, otherwise the authentication is not overridden.
