import httpx
import pytest
from locust import events
from locust.env import Environment

from src.tests.__common.clients.httpx_client import HttpClient
from src.tests.__common.decorators.transaction import Transaction

REQUEST_NAME = "ur_test_1.1_rest_get_/ping"


def make_client(handler) -> HttpClient:
    return HttpClient(
        timeout=1.0,
        client_url="http://test.local",
        environment=Environment(events=events),
        transport=httpx.MockTransport(handler),
    )


def http_events(fired):
    return [event for event in fired if event["request_type"] == "HTTP"]


def test_success_response_is_reported(fired_requests):
    client = make_client(lambda request: httpx.Response(200, text="pong"))

    client.get("/ping", extensions={"request_name": REQUEST_NAME})

    [event] = http_events(fired_requests)
    assert event["name"] == REQUEST_NAME
    assert event["exception"] is None
    assert event["response_length"] == 4


def test_error_status_is_reported_as_failure(fired_requests):
    client = make_client(lambda request: httpx.Response(503))

    response = client.get("/ping", extensions={"request_name": REQUEST_NAME})

    assert response.status_code == 503
    [event] = http_events(fired_requests)
    assert isinstance(event["exception"], httpx.HTTPStatusError)


def test_request_name_falls_back_to_path(fired_requests):
    client = make_client(lambda request: httpx.Response(200))

    client.get("/ping")

    [event] = http_events(fired_requests)
    assert event["name"] == "/ping"


@pytest.mark.parametrize("error_type", [httpx.ConnectError, httpx.ReadTimeout])
def test_transport_error_is_reported_and_raised(fired_requests, error_type):
    def handler(request):
        raise error_type("no response", request=request)

    client = make_client(handler)

    with pytest.raises(error_type):
        client.get("/ping", extensions={"request_name": REQUEST_NAME})

    [event] = http_events(fired_requests)
    assert event["name"] == REQUEST_NAME
    assert isinstance(event["exception"], error_type)
    assert event["response_time"] >= 0


def test_error_status_fails_enclosing_transaction(fired_requests):
    client = make_client(lambda request: httpx.Response(500))

    @Transaction("uc_test_1_rest_ping")
    def task():
        client.get("/ping", extensions={"request_name": REQUEST_NAME})

    task()

    [transaction] = [event for event in fired_requests if event["request_type"] == "TRANSACTION"]
    assert isinstance(transaction["exception"], httpx.HTTPStatusError)
