from collections.abc import Iterator

import pytest

from app.main import reset_rate_limits


@pytest.fixture(autouse=True)
def fresh_rate_limits() -> Iterator[None]:
    """Each test starts with empty rate-limit counters."""
    reset_rate_limits()
    yield
    reset_rate_limits()
