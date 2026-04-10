import threading

from locust import events
from prometheus_client import Counter, Histogram, start_http_server

PROMETHEUS_PORT = 9646


class PrometheusServerManager:
    _started = False
    _lock = threading.Lock()

    @classmethod
    def start(cls, port: int = PROMETHEUS_PORT):
        with cls._lock:
            if cls._started:
                print("⚠️ Prometheus сервер уже запущен")
                return

            try:
                start_http_server(port)
                cls._started = True
                print(f"🚀 Prometheus metrics: http://localhost:{port}/metrics")
            except OSError as e:
                if "Address already in use" in str(e):
                    print(f"⚠️ Порт {port} занят, метрики доступны")
                else:
                    print(f"❌ Ошибка запуска Prometheus: {e}")


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
    def _get_status_code(response, context):
        if response and hasattr(response, "status_code"):
            return str(response.status_code)
        elif context and hasattr(context, "status_code"):
            return str(context.status_code)
        elif context and context.get("response") and hasattr(context["response"], "status_code"):
            return str(context["response"].status_code)
        return "0"

    @classmethod
    def on_request(cls, request_type, name, response_time, response_length,
                   response=None, context=None, **kwargs):
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
def on_locust_init(environment, **kwargs):
    PrometheusServerManager.start()
    print("✅ Locust init: метрики готовы")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length,
               response=None, context=None, **kwargs):
    PrometheusMetricsSender.on_request(
        request_type=request_type,
        name=name,
        response_time=response_time,
        response_length=response_length,
        response=response,
        context=context,
        **kwargs,
    )
