from sdkite.adapter import Adapter, AdapterSpec
from sdkite.client import Client
from sdkite.exceptions import SDKiteError
from sdkite.pagination import Pagination, paginated

try:
    from sdkite._version import __version__
except ImportError:  # pragma: no cover
    __version__ = "0.0.0.dev0-unknown"


__all__ = (
    # sdkite._version
    "__version__",
    # sdkite.adapter
    "Adapter",
    "AdapterSpec",
    # sdkite.client
    "Client",
    # sdkite.exceptions
    "SDKiteError",
    # sdkite.pagination
    "Pagination",
    "paginated",
)
