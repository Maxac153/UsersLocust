import pytest
from locust import events


@pytest.fixture
def fired_requests():
    captured: list[dict] = []

    def listener(**kwargs):
        captured.append(kwargs)

    events.request.add_listener(listener)
    yield captured
    events.request.remove_listener(listener)
