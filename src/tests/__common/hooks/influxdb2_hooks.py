import os
import time
from dataclasses import dataclass
from typing import Any, Callable

from influxdb_client import InfluxDBClient, Point, WriteOptions
from locust import events
from reactivex.scheduler import ThreadPoolScheduler

from src.tests.__common.helpers.logger_helper import LoggerHelper

MEASUREMENT = "locust_requests"
MAX_ERROR_LENGTH = 500

# The client batches and flushes in its own thread; limits are explicit because the defaults
# (retries up to 3 min, close() waits up to 5 min) make a test hang on exit when InfluxDB is down.
# Trade-off: an InfluxDB outage longer than MAX_RETRY_TIME_MS drops the affected batches.
MAX_RETRY_TIME_MS = 30_000


def default_write_options() -> WriteOptions:
    # WriteOptions' default write_scheduler is one module-level pool that WriteApi.close() never shuts down;
    # its non-daemon worker keeps the locust process alive after "Shutting down", so each writer owns its pool
    return WriteOptions(
        batch_size=1_000,
        flush_interval=5_000,
        jitter_interval=1_000,
        retry_interval=2_000,
        max_retries=5,
        max_retry_delay=10_000,
        max_retry_time=MAX_RETRY_TIME_MS,
        max_close_wait=MAX_RETRY_TIME_MS + 5_000,
        write_scheduler=ThreadPoolScheduler(max_workers=1),
    )


@dataclass(frozen=True)
class InfluxSettings:
    url: str
    bucket: str
    org: str
    token: str

    @classmethod
    def from_env(cls) -> "InfluxSettings":
        return cls(
            url=os.getenv("DATASOURCE_URL", "http://localhost:8086"),
            bucket=os.getenv("INFLUX_BUCKET", "metrics"),
            org=os.getenv("INFLUX_ORG", "monitoring"),
            token=os.getenv("INFLUX_TOKEN", "super-secret-token"),
        )


def get_status_code(response: Any = None, context: Any = None) -> int:
    if response is not None and hasattr(response, "status_code"):
        return int(response.status_code)
    if hasattr(context, "status_code"):
        return int(context.status_code)
    if isinstance(context, dict) and hasattr(context.get("response"), "status_code"):
        return int(context["response"].status_code)
    return 0


def build_point(
        request_type: str,
        name: str,
        response_time: float,
        response_length: int | None,
        response: Any = None,
        context: Any = None,
        exception: BaseException | None = None,
) -> Point:
    point = (
        Point(MEASUREMENT)
        .tag("request_type", request_type)
        .tag("name", name)
        .field("response_time_ms", float(response_time))
        .field("response_length", int(response_length or 0))
        .field("success", 1 if exception is None else 0)
        .field("status_code", get_status_code(response, context))
        .time(time.time_ns())
    )
    if exception is not None:
        point = point.field("error", str(exception)[:MAX_ERROR_LENGTH])
    return point


def count_lines(data: str | bytes) -> int:
    text = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data
    return len(text.splitlines())


class InfluxMetricsWriter:
    __logger = LoggerHelper.setup_logger("influxdb2", date_time_now="influxdb2")

    def __init__(
            self,
            settings: InfluxSettings,
            client_factory: Callable[..., InfluxDBClient] = InfluxDBClient,
            write_options: WriteOptions | None = None,
    ) -> None:
        self.settings = settings
        self.client_factory = client_factory
        self.write_options = write_options or default_write_options()
        self.client = None
        self.write_api = None

    def start(self) -> None:
        self.client = self.client_factory(url=self.settings.url, token=self.settings.token, org=self.settings.org)
        self.write_api = self.client.write_api(
            write_options=self.write_options,
            error_callback=self._on_batch_error,
        )

    def on_request(self, **request_event: Any) -> None:
        if self.write_api is None:
            return
        point = build_point(**self._point_arguments(request_event))
        self.write_api.write(bucket=self.settings.bucket, org=self.settings.org, record=point)

    def stop(self) -> None:
        # close() is the only call that flushes pending batches; WriteApi.flush() is a no-op in influxdb-client
        if self.write_api is not None:
            self.write_api.close()
            self.write_api = None
        if self.client is not None:
            self.client.close()
            self.client = None
        self.write_options.write_scheduler.executor.shutdown(wait=False)

    @staticmethod
    def _point_arguments(request_event: dict[str, Any]) -> dict[str, Any]:
        keys = ("request_type", "name", "response_time", "response_length", "response", "context", "exception")
        return {key: request_event.get(key) for key in keys}

    def _on_batch_error(self, _conf: tuple[str, str, str], data: str | bytes, error: Exception) -> None:
        self.__logger.error("Influx Batch Dropped (%d Points): %s", count_lines(data), error)


writer = InfluxMetricsWriter(InfluxSettings.from_env())


@events.init.add_listener
def on_init(environment, **kwargs) -> None:
    writer.start()


@events.request.add_listener
def on_request(**kwargs) -> None:
    writer.on_request(**kwargs)


@events.quitting.add_listener
def on_quit(environment, **kwargs) -> None:
    writer.stop()
