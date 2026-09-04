from jarvis.infrastructure.redis_store import InMemoryCache


def test_memory_cache_roundtrip() -> None:
    cache = InMemoryCache()
    cache.set("a", {"value": 1}, ttl_seconds=10)
    assert cache.get("a") == {"value": 1}
    cache.delete("a")
    assert cache.get("a") is None
