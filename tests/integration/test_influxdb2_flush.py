import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from influxdb_client import WriteOptions
from reactivex.scheduler import ThreadPoolScheduler

from src.tests.__common.hooks.influxdb2_hooks import InfluxMetricsWriter, InfluxSettings


class InfluxWriteStub(BaseHTTPRequestHandler):
    received: list[str] = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        type(self).received.append(body.decode())
        self.send_response(204)
        self.end_headers()

    def log_message(self, *_args):
        pass


@pytest.fixture
def influx_stub():
    InfluxWriteStub.received = []
    server = HTTPServer(("127.0.0.1", 0), InfluxWriteStub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", InfluxWriteStub.received
    server.shutdown()


def settings(url: str) -> InfluxSettings:
    return InfluxSettings(url=url, bucket="metrics", org="monitoring", token="token")


def single_request_event() -> dict:
    return {"request_type": "HTTP", "name": "ur_single", "response_time": 1.0, "response_length": 0}


def test_single_request_is_flushed_on_stop(influx_stub):
    url, received = influx_stub
    writer = InfluxMetricsWriter(settings(url))
    writer.start()

    writer.on_request(**single_request_event())
    writer.stop()

    assert any("ur_single" in body for body in received)


def test_stop_is_bounded_when_influx_is_down():
    options = WriteOptions(flush_interval=100, retry_interval=100, max_retries=2,
                           max_retry_delay=200, max_retry_time=500, max_close_wait=2_000,
                           write_scheduler=ThreadPoolScheduler(max_workers=1))
    writer = InfluxMetricsWriter(settings("http://127.0.0.1:1"), write_options=options)
    writer.start()
    writer.on_request(**single_request_event())

    started = time.monotonic()
    writer.stop()

    assert time.monotonic() - started < 5
