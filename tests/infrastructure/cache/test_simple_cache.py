import pytest

from src.infrastructure.cache.simple_cache import SimpleCache


def test_invalid_computed_value_is_never_cached():
    cache = SimpleCache()
    calls = 0

    def compute():
        nonlocal calls
        calls += 1
        return {}

    with pytest.raises(ValueError, match="failed validation"):
        cache.get_or_compute("league", compute, validator=bool)
    with pytest.raises(ValueError, match="failed validation"):
        cache.get_or_compute("league", compute, validator=bool)

    assert calls == 2
    assert cache.get_stats()["size"] == 0


def test_valid_computed_value_is_reused():
    cache = SimpleCache()
    calls = 0

    def compute():
        nonlocal calls
        calls += 1
        return {"DET": 1}

    assert cache.get_or_compute("league", compute, validator=bool) == {"DET": 1}
    assert cache.get_or_compute("league", compute, validator=bool) == {"DET": 1}
    assert calls == 1
