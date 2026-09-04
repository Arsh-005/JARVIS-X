from jarvis.infrastructure.rate_limit import TokenBucket


def test_token_bucket_denies_after_capacity() -> None:
    bucket = TokenBucket(rate_per_second=0.0001, capacity=2)
    assert bucket.allow()
    assert bucket.allow()
    assert not bucket.allow()
