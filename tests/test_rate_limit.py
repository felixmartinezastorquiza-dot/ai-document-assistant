from fastapi.testclient import TestClient
from starlette.requests import Request

from app.main import app, get_chat_model, get_retriever
from app.rate_limit import DailyQuota, SlidingWindowRateLimiter, client_ip
from tests.test_chat_api import StubChatModel, StubRetriever


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_allows_requests_up_to_the_limit_then_blocks() -> None:
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60, clock=FakeClock())

    assert [limiter.check("1.2.3.4") for _ in range(3)] == [None, None, None]
    assert limiter.check("1.2.3.4") == 60


def test_window_slides_so_old_requests_stop_counting() -> None:
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60, clock=clock)
    limiter.check("ip")
    clock.now += 30
    limiter.check("ip")

    clock.now += 31  # the first request is now older than 60 s
    assert limiter.check("ip") is None
    assert limiter.check("ip") is not None


def test_each_visitor_has_its_own_limit() -> None:
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60, clock=FakeClock())

    assert limiter.check("visitor-a") is None
    assert limiter.check("visitor-b") is None
    assert limiter.check("visitor-a") is not None


def test_daily_quota_resets_on_a_new_day() -> None:
    day = {"value": "2026-01-01"}
    quota = DailyQuota(max_per_day=2, today=lambda: day["value"])

    assert [quota.consume() for _ in range(3)] == [True, True, False]
    day["value"] = "2026-01-02"
    assert quota.consume() is True


def make_request(forwarded_for: str | None, socket_ip: str = "10.0.0.1") -> Request:
    headers = [(b"x-forwarded-for", forwarded_for.encode())] if forwarded_for else []
    return Request({"type": "http", "headers": headers, "client": (socket_ip, 1234)})


def test_client_ip_uses_socket_address_when_no_proxy_is_trusted() -> None:
    assert client_ip(make_request("6.6.6.6"), trusted_proxy_hops=0) == "10.0.0.1"


def test_client_ip_ignores_spoofed_entries_behind_one_proxy() -> None:
    # The client forged "6.6.6.6"; the proxy appended the real address last.
    request = make_request("6.6.6.6, 203.0.113.7")

    assert client_ip(request, trusted_proxy_hops=1) == "203.0.113.7"


def test_chat_endpoint_returns_429_after_the_per_ip_limit() -> None:
    app.dependency_overrides[get_retriever] = StubRetriever
    app.dependency_overrides[get_chat_model] = StubChatModel
    client = TestClient(app)
    try:
        statuses = [
            client.post("/chat", json={"question": "Parking?"}).status_code for _ in range(11)
        ]
    finally:
        app.dependency_overrides.clear()

    assert statuses[:10] == [200] * 10
    assert statuses[10] == 429


def test_client_ip_behind_cloudflare_and_render_ignores_spoofed_entries() -> None:
    # Real header shape observed in production (client, Cloudflare, Render internal).
    request = make_request("6.6.6.6,190.0.2.10, 162.159.114.82, 10.24.128.209")

    assert client_ip(request, trusted_proxy_hops=3) == "190.0.2.10"
