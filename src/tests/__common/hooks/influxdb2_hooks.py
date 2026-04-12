import os
import queue
import threading
import time

from influxdb_client import InfluxDBClient, Point, WriteOptions
from locust import events

from src.tests.__common.helpers.logger_helper import LoggerHelper


class InfluxMetricsWriter:
    __logger = LoggerHelper.setup_logger("influxdb2", date_time_now="influxdb2")

    def __init__(self):
        self.write_api = None
        self.influx_client = None
        self.metrics_queue = queue.Queue()
        self.background_thread = None
        self.stop_background = threading.Event()
        self.url = os.getenv("DATASOURCE_URL", "http://localhost:8086")
        self.bucket = os.getenv("INFLUX_BUCKET", "metrics")
        self.org = os.getenv("INFLUX_ORG", "monitoring")
        self.token = os.getenv("INFLUX_TOKEN", "super-secret-token")

    @staticmethod
    def get_status_code(response=None, context=None) -> int:
        if response and hasattr(response, "status_code"):
            return int(response.status_code)
        if context:
            if hasattr(context, "status_code"):
                return int(context.status_code)
            if isinstance(context, dict):
                resp = context.get("response")
                if resp and hasattr(resp, "status_code"):
                    return int(resp.status_code)
        return 0

    def start(self) -> None:
        self.influx_client = InfluxDBClient(
            url=self.url,
            token=self.token,
            org=self.org,
        )
        self.write_api = self.influx_client.write_api(
            write_options=WriteOptions(
                batch_size=1000,
                flush_interval=5000,
                jitter_interval=1000,
                retry_interval=5000,
                max_retries=5,
            )
        )
        self.background_thread = threading.Thread(target=self.background_writer, daemon=True)
        self.background_thread.start()

    def background_writer(self) -> None:
        batch = []
        last_send = time.time()

        while not self.stop_background.is_set():
            try:
                while not self.stop_background.is_set():
                    now = time.time()
                    time_to_send_by_timer = now - last_send >= 10.0
                    batch_size_reached = len(batch) >= 10_000

                    if batch_size_reached or time_to_send_by_timer:
                        if batch and self.write_api is not None:
                            try:
                                self.write_api.write(
                                    bucket=self.bucket,
                                    org=self.org,
                                    record=batch,
                                )
                            except Exception as e:
                                self.__logger.error(f"Influx Write Error: {e}")
                            batch = []
                            last_send = now
                        break

                    try:
                        item = self.metrics_queue.get(timeout=0.1)
                        batch.append(item)
                    except queue.Empty:
                        pass

            except Exception as e:
                self.__logger.error(f"Background Writer Error: {e}")

    def on_request(
            self,
            request_type,
            name,
            response_time,
            response_length,
            response=None,
            context=None,
            exception=None,
            **kwargs
    ) -> None:
        if self.influx_client is None:
            return

        status_code = self.get_status_code(response=response, context=context)
        point = (
            Point("locust_requests")
            .tag("request_type", request_type)
            .tag("name", name)
            .field("response_time_ms", float(response_time))
            .field("response_length", int(response_length or 0))
            .field("success", 1 if exception is None else 0)
            .field("status_code", int(status_code))
            .time(time.time_ns())
        )

        if exception is not None:
            point = point.field("error", str(exception)[:500])

        self.metrics_queue.put(point)

    def stop(self):
        self.stop_background.set()

        batch = []
        while not self.metrics_queue.empty():
            try:
                item = self.metrics_queue.get(timeout=0.1)
                batch.append(item)
            except queue.Empty:
                break

        if batch and self.write_api is not None:
            try:
                self.write_api.write(
                    bucket=self.bucket,
                    org=self.org,
                    record=batch,
                )
            except Exception as e:
                self.__logger.error(f"Final Flush Error: {e}")

        if self.write_api is not None:
            self.write_api.flush()
        if self.influx_client is not None:
            self.influx_client.close()


writer = InfluxMetricsWriter()


@events.init.add_listener
def on_init(environment, **kwargs):
    writer.start()


@events.request.add_listener
def on_request(
        request_type,
        name,
        response_time,
        response_length,
        response=None,
        context=None,
        exception=None,
        **kwargs
):
    writer.on_request(
        request_type=request_type,
        name=name,
        response_time=response_time,
        response_length=response_length,
        response=response,
        context=context,
        exception=exception,
        **kwargs,
    )


@events.quitting.add_listener
def on_quit(environment, **kwargs):
    writer.stop()
