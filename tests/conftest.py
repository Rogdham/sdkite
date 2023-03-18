from pathlib import Path
import sys
from typing import List

import pytest


def pytest_collection_modifyitems(
    # pylint: disable=unused-argument
    config: pytest.Config,  # noqa: ARG001
    items: List[pytest.Item],
) -> None:
    root = Path(__file__).parent.parent
    for item in items:
        relative = Path(item.fspath).parent.relative_to(root)
        mark = next(part for part in relative.parts if part != "tests")
        item.add_marker(getattr(pytest.mark, mark))


# skipping some files due to syntax not yet supported
collect_ignore: List[str] = []
if sys.version_info < (3, 8):
    collect_ignore.append("unit/test_pagination_pep570.py")
