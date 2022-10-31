from sdkite.adapter import Adapter, AdapterSpec
from sdkite.client import Client
from sdkite.pagination import Pagination, paginated

try:
    from sdkite._version import __version__
except ImportError:  # pragma: no cover
    __version__ = "0.0.0.dev0-unknown"


__all__ = (
    "__version__",
    "Adapter",
    "AdapterSpec",
    "Client",
    "paginated",
    "Pagination",
)
