# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project
adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

[unreleased]: https://github.com/rogdham/bigxml/compare/v0.1.0...HEAD

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

## [0.1.0] - 2020-10-31

[0.1.0]: https://github.com/rogdham/sdkite/releases/tag/v0.1.0

### :rocket: Added

- Initial public release :tada:
