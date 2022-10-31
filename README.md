<div align="center">

# SDKite

A simple framework for building SDKs and API clients

[![GitHub build status](https://img.shields.io/github/workflow/status/rogdham/sdkite/build/master)](https://github.com/rogdham/sdkite/actions?query=branch:master)
[![Release on PyPI](https://img.shields.io/pypi/v/sdkite)](https://pypi.org/project/sdkite/)
[![Code coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/rogdham/sdkite/search?q=fail+under&type=Code)
[![Mypy type checker](https://img.shields.io/badge/type_checker-mypy-informational)](https://mypy.readthedocs.io/)
[![MIT License](https://img.shields.io/pypi/l/sdkite)](https://github.com/Rogdham/sdkite/blob/master/LICENSE.txt)

---

[📃 Changelog](./CHANGELOG.md)

</div>

---

This project is under heavy development. Breaking changes in future versions are to be
expected.

Main points before alpha version:

- [ ] Documentation
- [ ] Handle retrying
- [ ] Improve HTTP adapter
  - [ ] Support for more request body types
  - [ ] Handle _bad_ status codes
  - [ ] Builtin auth handlers like basic auth / bearer token
  - [ ] Usual shortcuts like `.get(...)` for `.request('get', ...)`
  - [ ] Allow to disable interceptors on a specific request
  - [ ] Wrapt `requests`' exceptions
  - [ ] Support more HTTP adapters
- [ ] Remove `requests` from dependencies
- [ ] And more!
