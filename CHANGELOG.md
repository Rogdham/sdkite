# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project
adheres to [Semantic Versioning](https://semver.org/).

## [0.5.0] - 2023-05-07

[0.5.0]: https://github.com/rogdham/sdkite/compare/v0.4.0...v0.5.0

v0.5.0 works on unexpected cases: exceptions & HTTP status codes

### :boom: Breaking changes

- By default, an exception is raised when an HTTP responses has a non-200 status codes
- All exceptions raised by HTTP engines are now instances of `HTTPError`

### :rocket: Added

- Allow to specify expected status codes of HTTP responses with the
  `expected_status_codes` parameter
- The response returned by HTTP engines can be used as a context manager; in that case,
  exceptions happening within the context manager are re-raised though
  `HTTPContextError`, which gives the context in which the exception ocurred; this is
  also useful to clean resources for certain HTTP engines

## [0.4.0] - 2023-04-16

[0.4.0]: https://github.com/rogdham/sdkite/compare/v0.3.0...v0.4.0

v0.4.0 introduces request retrying and timeout

### :boom: Breaking changes

- The requests HTTP engine is now using a timeout of 40 seconds for connection and 30
  seconds afterwards (or 10 minutes in case of streaming)
- `HTTPAdapterSpec`'s `headers` parameter is now keyword-only

### :rocket: Added

- HTTP requests are now retried several times in case of exception; this behavior can be
  modified with the following parameters: `retry_nb_attempts`, `retry_wait_initial`,
  `retry_wait_max`, `retry_wait_jitter`, and `retry_callback` allows to be notified when
  a retry is performed

### :bug: Fixes

- Warnings due to wrong usage are now using `UserWarning` instead of `RuntimeWarning`

### :house: Internal

- Add `Adapter._from_adapter_hierarchy` to get easy access to values from the adapter
  hierarchy
- Simplify `assert_type` imports following `typing-extensions` requirement on Python up
  to 3.10
- Necessary code changes following dev dependency update: mypy

## [0.3.0] - 2023-02-26

[0.3.0]: https://github.com/rogdham/sdkite/compare/v0.2.0...v0.3.0

v0.3.0 allows HTTP responses to be recorded to be replayed later

### :rocket: Added

- Allow to select HTTP engine with `HTTPAdapterSpec.set_engine`
- Add HTTP replay engine to be able to record/replay HTTP responses

### :house: Internal

- Rename HTTP “impl” into “engine”
- Upgrade `typing-extensions` dependency
- Necessary code changes following dev dependency update: mypy

## [0.2.0] - 2023-01-01

[0.2.0]: https://github.com/rogdham/sdkite/compare/v0.1.0...v0.2.0

v0.2.0 expends the public API and adds documentation

### :rocket: Added

- Usual shortcuts to `HTTPAdapter.requests(method, ...)`: `.get`, `.options`, `.head`,
  `.post`, `.put`, `.patch`, `.delete`
- Add `BasicAuth` and `NoAuth` helpers for HTTP authorization management
- `HTTPBodyEncoding` support for conversion of more object types: in addition to
  `None`/`bytes`/`str`, add support for `bool`/`int`/`float`, as well as
  `list`/`tuple`/`set`/`dict` of other supported types (recursively).

### :memo: Documentation

- First version of the documentation

### :house: Internal

- Necessary code changes following dev dependency update: mypy
- Fix a badge shield URL in readme

## [0.1.0] - 2022-10-31

[0.1.0]: https://github.com/rogdham/sdkite/releases/tag/v0.1.0

### :rocket: Added

- Initial public release :tada:
