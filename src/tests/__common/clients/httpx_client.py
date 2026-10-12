import logging
from typing import Any, TypedDict

from httpx import URL, BaseTransport, Client, QueryParams, RequestError, Response
from locust.env import Environment

from src.tests.__common.hooks.event_hooks import EventHooks


class ClientExtensions(TypedDict, total=False):
    request_name: str


class HttpClient:
    def __init__(
            self,
            timeout: float | int,
            client_url: str,
            environment: Environment | None = None,
            transport: BaseTransport | None = None,
    ) -> None:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        self.environment = environment
        event_hooks = {}

        if environment:
            event_hooks = {
                "request": [EventHooks.locust_request_event_hook],
                "response": [EventHooks.locust_response_event_hook(environment)]
            }

        self.client = Client(
            timeout=timeout,
            base_url=client_url,
            event_hooks=event_hooks,
            transport=transport,
        )

    def get(
            self,
            url: URL | str,
            params: QueryParams | None = None,
            extensions: ClientExtensions | None = None
    ) -> Response:
        return self._send("GET", url, params=params, extensions=extensions)

    def post(
            self,
            url: URL | str,
            json: Any | None = None,
            extensions: ClientExtensions | None = None
    ) -> Response:
        return self._send("POST", url, json=json, extensions=extensions)

    def close(self) -> None:
        self.client.close()

    def _send(self, method: str, url: URL | str, **kwargs: Any) -> Response:
        # Re-raise: the task cannot go on without a response, and the enclosing transaction must fail
        try:
            return self.client.request(method, url, **kwargs)
        except RequestError as error:
            if self.environment is not None:
                EventHooks.fire_transport_error(self.environment, error)
            raise
