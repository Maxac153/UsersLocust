from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.tests.__common.hooks.influxdb2_hooks import (
    InfluxMetricsWriter,
    InfluxSettings,
    build_point,
    count_lines,
    get_status_code,
)

SETTINGS = InfluxSettings(url="http://influx.local", bucket="metrics", org="monitoring", token="token")


def request_event(**overrides):
    event = {
        "request_type": "HTTP",
        "name": "ur_test",
        "response_time": 12.5,
        "response_length": 10,
        "response": SimpleNamespace(status_code=200),
        "context": None,
        "exception": None,
    }
    return {**event, **overrides}


class TestGetStatusCode:
    @pytest.mark.parametrize("response, context, expected", [
        (SimpleNamespace(status_code=503), None, 503),
        (None, SimpleNamespace(status_code=404), 404),
        (None, {"response": SimpleNamespace(status_code=201)}, 201),
        (None, {}, 0),
        (None, None, 0),
    ])
    def test_sources(self, response, context, expected):
        assert get_status_code(response, context) == expected


class TestBuildPoint:
    def test_success_point(self):
        line = build_point(**request_event()).to_line_protocol()

        assert line.startswith("locust_requests,name=ur_test,request_type=HTTP ")
        assert "response_time_ms=12.5" in line
        assert "status_code=200i" in line
        assert "success=1i" in line
        assert "error=" not in line

    def test_failure_point_truncates_error(self):
        line = build_point(**request_event(exception=RuntimeError("x" * 1000))).to_line_protocol()

        assert "success=0i" in line
        assert f'error="{"x" * 500}"' in line

    def test_missing_response_length_is_zero(self):
        line = build_point(**request_event(response_length=None)).to_line_protocol()

        assert "response_length=0i" in line


@pytest.mark.parametrize("data, expected", [(b"a 1\nb 2", 2), ("a 1", 1), (b"", 0)])
def test_count_lines(data, expected):
    assert count_lines(data) == expected


class TestInfluxMetricsWriter:
    def make_writer(self):
        client = MagicMock()
        return InfluxMetricsWriter(SETTINGS, client_factory=lambda **_: client), client

    def test_ignores_requests_before_start(self):
        writer, client = self.make_writer()

        writer.on_request(**request_event())

        client.write_api.assert_not_called()

    def test_writes_point_to_configured_bucket(self):
        writer, client = self.make_writer()
        writer.start()

        writer.on_request(**request_event())

        write = client.write_api.return_value.write
        write.assert_called_once()
        assert write.call_args.kwargs["bucket"] == "metrics"
        assert write.call_args.kwargs["org"] == "monitoring"

    def test_stop_closes_write_api_before_client(self):
        writer, client = self.make_writer()
        writer.start()

        writer.stop()

        assert [call[0] for call in client.mock_calls if call[0].endswith("close")] == [
            "write_api().close",
            "close",
        ]

    def test_stop_is_idempotent_and_safe_before_start(self):
        writer, client = self.make_writer()

        writer.stop()
        writer.start()
        writer.stop()
        writer.stop()

        client.close.assert_called_once()

    def test_stop_shuts_down_own_write_scheduler(self):
        writer, _ = self.make_writer()
        writer.start()

        writer.stop()

        with pytest.raises(RuntimeError):
            writer.write_options.write_scheduler.executor.submit(lambda: None)

    def test_each_writer_owns_its_write_scheduler(self):
        first, _ = self.make_writer()
        second, _ = self.make_writer()

        assert first.write_options.write_scheduler is not second.write_options.write_scheduler
