import logging
from typing import Any, TypedDict

from httpx import Client, URL, Response, QueryParams
from locust.env import Environment

from src.tests.__common.hooks.event_hooks import locust_request_event_hook, locust_response_event_hook


class ClientExtensions(TypedDict, total=False):
    """
    Специальный словарь расширений запроса.
    Используется для передачи метаданных, не относящихся к телу запроса.

    В нашем случае — это `route`, который нужен, чтобы подменять
    динамические пути (например: /accounts/123) на шаблонные
    (например: /accounts/{id}) при передаче метрик в Locust.
    """
    request_name: str


class BaseClient:
    """
    Абстрактный HTTP-клиент, инкапсулирующий методы get/post
    и работу с extensions. Основан на httpx.Client.
    """

    def __init__(self, client: Client):
        """
        Инициализатор принимает уже настроенный httpx.Client,
        в котором могут быть прописаны timeout, base_url, event_hooks и т.д.
        """
        self.client = client

    def get(
            self,
            url: URL | str,
            params: QueryParams | None = None,
            extensions: ClientExtensions | None = None
    ) -> Response:
        """
        Отправляет GET-запрос и, при необходимости, передаёт route через extensions.
        Это нужно для корректной агрегации статистики.
        """
        return self.client.get(url, params=params, extensions=extensions)

    def post(
            self,
            url: URL | str,
            json: Any | None = None,
            extensions: ClientExtensions | None = None
    ) -> Response:
        """
        POST-запрос с поддержкой кастомных расширений.
        """
        return self.client.post(url, json=json, extensions=extensions)


def get_http_client(timeout: int, client_url: str) -> Client:
    """
    Конструктор базового клиента без хуков.
    Используется в сидинге или вспомогательных модулях.
    """
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return Client(timeout=timeout, base_url=client_url)


def get_locust_http_client(timeout: float, client_url: str, environment: Environment) -> Client:
    """
    Конструктор клиента с поддержкой хуков Locust.
    Используется во всех сценариях, где нужно собирать метрики.
    """
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return Client(
        timeout=timeout,
        base_url=client_url,
        event_hooks={
            "request": [locust_request_event_hook],
            "response": [locust_response_event_hook(environment)]
        }
    )
