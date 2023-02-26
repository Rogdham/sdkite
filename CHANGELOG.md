# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project
adheres to [Semantic Versioning](https://semver.org/).

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
