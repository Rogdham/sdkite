<div align="center">

# SDKite

A simple framework for building SDKs and API clients

[![GitHub build status](https://img.shields.io/github/actions/workflow/status/rogdham/sdkite/build.yml?branch=master)](https://github.com/rogdham/sdkite/actions?query=branch:master)
[![Release on PyPI](https://img.shields.io/pypi/v/sdkite)](https://pypi.org/project/sdkite/)
[![Code coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/rogdham/sdkite/search?q=fail+under&type=Code)
[![Mypy type checker](https://img.shields.io/badge/type_checker-mypy-informational)](https://mypy.readthedocs.io/)
[![MIT License](https://img.shields.io/pypi/l/sdkite)](https://github.com/Rogdham/sdkite/blob/master/LICENSE.txt)

---

[📖 Documentation](https://sdkite.rogdham.net/)&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;[📃 Changelog](./CHANGELOG.md)

</div>

---

This project is under heavy development. Breaking changes in future versions are to be
expected.

Main points before alpha version:

- [x] Minimal documentation
- [ ] Complete documentation
- [ ] Handle retrying
- [ ] Improve HTTP adapter
  - [x] Support for more request body types (basic types)
  - [ ] Support for even more request body types (files, iterables)
  - [ ] Handle _bad_ status codes
  - [x] Builtin auth handlers like basic auth
  - [x] Usual shortcuts like `.get(...)` for `.request('get', ...)`
  - [ ] Allow to disable interceptors on a specific request
  - [ ] Wrapt `requests`' exceptions
  - [ ] Support more HTTP adapters
- [ ] Remove `requests` from dependencies
- [ ] And more!
