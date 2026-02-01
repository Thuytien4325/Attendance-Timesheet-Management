import pytest


@pytest.fixture
def fixed_now():
    from datetime import datetime

    return datetime(2026, 1, 31, 8, 30, 0)
