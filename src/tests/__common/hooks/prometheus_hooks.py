import os
import threading

from locust import events
from prometheus_client import Counter, Histogram, start_http_server

from src.tests.__common.helpers.logger_helper import LoggerHelper


class PrometheusServerManager:
    _started = False
    _lock = threading.Lock()
    __logger = LoggerHelper.setup_logger("prometheus", date_time_now="influxdb2")

    @classmethod
    def start(cls, port: int = int(os.getenv("PROMETHEUS_PORT", "9646"))) -> None:
        with cls._lock:
            if cls._started:
                cls.__logger.warning("⚠️ Prometheus Server Is Already Running")
                return
            try:
                start_http_server(port)
                cls._started = True
                cls.__logger.info(f"🚀 Prometheus Metrics: http://localhost:{port}/metrics")
            except OSError as e:
                if "Address Already In Use" in str(e):
                    cls.__logger.warning(f"⚠️ Port {port} Is Busy, Metrics Are Available")
                else:
                    cls.__logger.error(f"❌ Prometheus Startup Error: {e}")


class PrometheusMetricsSender:
    REQUEST_COUNT = Counter(
        "locust_requests_total",
        "Total requests",
        ["method", "endpoint", "status"],
    )

    REQUEST_DURATION = Histogram(
        "locust_request_duration_seconds",
        "Request duration",
        ["method", "endpoint"],
    )

    @staticmethod
    def _get_status_code(response, context) -> str:
        if response and hasattr(response, "status_code"):
            return str(response.status_code)
        elif context and hasattr(context, "status_code"):
            return str(context.status_code)
        elif context and context.get("response") and hasattr(context["response"], "status_code"):
            return str(context["response"].status_code)
        return "0"

    @classmethod
    def on_request(
            cls,
            request_type,
            name,
            response_time,
            response_length,
            response=None,
            context=None,
            **kwargs
    ) -> None:
        status_code = cls._get_status_code(response, context)

        cls.REQUEST_COUNT.labels(
            method=request_type,
            endpoint=name,
            status=status_code,
        ).inc()

        cls.REQUEST_DURATION.labels(
            method=request_type,
            endpoint=name,
        ).observe(response_time / 1000.0)


@events.init.add_listener
def on_locust_init(environment, **kwargs) -> None:
    PrometheusServerManager.start()


@events.request.add_listener
def on_request(
        request_type,
        name,
        response_time,
        response_length,
        response=None,
        context=None,
        **kwargs
) -> None:
    PrometheusMetricsSender.on_request(
        request_type=request_type,
        name=name,
        response_time=response_time,
        response_length=response_length,
        response=response,
        context=context,
        **kwargs,
    )
