# HTTP Response

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
