import logging
from typing import Any, TypedDict

from httpx import Client, URL, Response, QueryParams
from locust.env import Environment

from src.tests.__common.hooks.event_hooks import EventHooks


class ClientExtensions(TypedDict, total=False):
    request_name: str


class HttpClient:
    def __init__(
            self,
            timeout: float | int,
            client_url: str,
            environment: Environment | None = None
    ):
        logging.getLogger("httpx").setLevel(logging.WARNING)
        event_hooks = {}

        if environment:
            event_hooks = {
                "request": [EventHooks.locust_request_event_hook],
                "response": [EventHooks.locust_response_event_hook(environment)]
            }

        self.client = Client(
            timeout=timeout,
            base_url=client_url,
            event_hooks=event_hooks
        )

    def get(
            self,
            url: URL | str,
            params: QueryParams | None = None,
            extensions: ClientExtensions | None = None
    ) -> Response:
        return self.client.get(url, params=params, extensions=extensions)

    def post(
            self,
            url: URL | str,
            json: Any | None = None,
            extensions: ClientExtensions | None = None
    ) -> Response:
        return self.client.post(url, json=json, extensions=extensions)

    def close(self):
        self.client.close()
