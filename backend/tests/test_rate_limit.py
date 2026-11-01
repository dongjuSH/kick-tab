import threading
import time

from starlette.requests import Request

from app.core.rate_limit import Limit, RateLimiter, client_ip, retry_after_header

TRUSTED = ["127.0.0.1", "::1"]


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def make_request(peer: str, forwarded: str | None = None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "client": (peer, 1234), "headers": headers})


def test_minute_and_day_windows_are_both_enforced():
    clock = FakeClock()
    limiter = RateLimiter([Limit(3, 60), Limit(5, 86400)], clock=clock)
    assert [limiter.hit("a") for _ in range(3)] == [None, None, None]
    wait = limiter.hit("a")
    assert wait is not None and 0 < wait <= 60
    assert limiter.hit("b") is None  # keys are independent

    clock.now += 61
    assert limiter.hit("a") is None
    assert limiter.hit("a") is None
    day_wait = limiter.hit("a")  # 5 per day reached
    assert day_wait is not None and day_wait > 60

    clock.now += 86400
    assert limiter.hit("a") is None


def test_rejected_requests_do_not_consume_quota():
    clock = FakeClock()
    limiter = RateLimiter([Limit(1, 60)], clock=clock)
    assert limiter.hit("a") is None
    for _ in range(10):
        assert limiter.hit("a") is not None
    clock.now += 60.5
    assert limiter.hit("a") is None


def test_retry_after_header_is_a_positive_integer():
    assert retry_after_header(0.2) == "1"
    assert retry_after_header(59.1) == "60"


def test_forwarded_for_is_ignored_from_untrusted_peer():
    assert client_ip(make_request("203.0.113.9", "198.51.100.1"), TRUSTED) == "203.0.113.9"


def test_forwarded_for_from_trusted_proxy_uses_right_most_untrusted_hop():
    # The browser spoofs 1.1.1.1; the proxy appends the real client 203.0.113.9.
    request = make_request("127.0.0.1", "1.1.1.1, 203.0.113.9")
    assert client_ip(request, TRUSTED) == "203.0.113.9"


def test_trusted_proxy_without_header_falls_back_to_peer():
    assert client_ip(make_request("::1"), TRUSTED) == "::1"
    assert client_ip(make_request("127.0.0.1", "not-an-ip"), TRUSTED) == "127.0.0.1"


def test_check_does_not_create_buckets_for_unknown_keys():
    limiter = RateLimiter([Limit(1, 60)])
    assert limiter.check("new") is None
    assert limiter.size == 0
    limiter.record("new")
    assert limiter.size == 1


def test_key_count_is_bounded_and_oldest_keys_are_evicted():
    clock = FakeClock()
    limiter = RateLimiter([Limit(5, 86400)], clock=clock, max_keys=100)
    for index in range(1000):
        clock.now += 0.001
        limiter.hit(f"k{index}")
    assert limiter.size == 100
    assert limiter.check("k999") is None  # most recent keys are kept


def _run_concurrently(count: int, action) -> list:
    barrier = threading.Barrier(count)
    results: list = []
    lock = threading.Lock()

    def worker() -> None:
        barrier.wait()
        outcome = action()
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=worker) for _ in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    return results


def test_concurrent_hits_on_one_key_allow_only_the_limit():
    """hit() must check and record under one lock (re-review A)."""

    def slow_clock() -> float:
        time.sleep(0.01)  # widens any gap between checking and recording
        return time.monotonic()

    limiter = RateLimiter([Limit(1, 60)], clock=slow_clock)
    results = _run_concurrently(8, lambda: limiter.hit("same"))
    assert sum(result is None for result in results) == 1
    assert limiter.size == 1


def test_concurrent_requests_through_rate_limit_allow_only_the_limit():
    from app.api.deps import RateLimit
    from app.api.errors import ApiError

    limit = RateLimit(
        "probe", [Limit(1, 60)], key_func=lambda request: "same", global_limits=[Limit(5, 60)]
    )
    request = Request({"type": "http", "headers": []})

    def call() -> bool:
        try:
            limit(request)
        except ApiError:
            return False
        return True

    results = _run_concurrently(8, call)
    assert results.count(True) == 1
