"""Prometheus метрики для Locust"""

from locust import events
from prometheus_client import Counter, Histogram, start_http_server

PROMETHEUS_PORT = 9646

# Глобальные метрики (доступны всем пользователям)
REQUEST_COUNT = Counter(
    'locust_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'locust_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint']
)


def start_prometheus_server():
    """Запускает Prometheus HTTP сервер"""
    start_http_server(PROMETHEUS_PORT)
    print(f"🚀 Prometheus metrics: http://localhost:{PROMETHEUS_PORT}/metrics")


def hook_request_metrics():
    """Подключает глобальный обработчик всех запросов"""

    @events.request.add_listener
    def on_request(request_type, name, response_time, response_length,
                   response=None, context=None, **kwargs):
        """Автоматически захватывает ВСЕ запросы из всех @task методов"""
        status_code = _get_status_code(response, context)

        REQUEST_COUNT.labels(
            method=request_type,
            endpoint=name,
            status=status_code
        ).inc()

        REQUEST_DURATION.labels(
            method=request_type,
            endpoint=name
        ).observe(response_time / 1000.0)


def _get_status_code(response, context):
    """Извлекает статус код из response или context"""
    if response and hasattr(response, 'status_code'):
        return response.status_code
    elif context and hasattr(context, 'status_code'):
        return context.status_code
    elif context and context.get('response') and hasattr(context['response'], 'status_code'):
        return context['response'].status_code
    return 0
