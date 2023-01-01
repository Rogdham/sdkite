# Typing

_SDKite_ commes natively with type hints, which are checked by [_mypy_][mypy].

The benefits are twofold:

- Improve the correctness of the code of the library itself;
- Allow users of the library to benefit from well-defined type hints on the public API.

As a rule of thumbs, we follow [Postel's law][postels_law] by being as vague as possible
for the arguments of functions, and as precise as possible for the returned values.

[mypy]: https://mypy.readthedocs.io/en/stable/index.html
[postels_law]: https://en.wikipedia.org/wiki/Robustness_principle

<!-- FIXME add examples -->
