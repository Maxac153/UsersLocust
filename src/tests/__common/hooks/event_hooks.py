import time

from httpx import HTTPStatusError, Request, RequestError, Response
from locust.env import Environment

REQUEST_TYPE = "HTTP"


class EventHooks:
    @staticmethod
    def locust_request_event_hook(request: Request) -> None:
        request.extensions["start_time"] = time.time()

    @staticmethod
    def locust_response_event_hook(environment: Environment):
        def inner(response: Response) -> None:
            exception: HTTPStatusError | None = None
            try:
                response.raise_for_status()
            except HTTPStatusError as error:
                exception = error

            request = response.request
            response_time = EventHooks._elapsed_ms(request)
            environment.events.request.fire(
                request_type=REQUEST_TYPE,
                name=EventHooks._request_name(request),
                response_time=response_time,
                response_length=len(response.read()),
                response=response,
                exception=exception,
                context=None,
            )

        return inner

    @staticmethod
    def fire_transport_error(environment: Environment, error: RequestError) -> None:
        # Response hooks never run when there is no response (connect error, timeout), so report it here
        request = error.request
        environment.events.request.fire(
            request_type=REQUEST_TYPE,
            name=EventHooks._request_name(request),
            response_time=EventHooks._elapsed_ms(request),
            response_length=0,
            response=None,
            exception=error,
            context=None,
        )

    @staticmethod
    def _request_name(request: Request) -> str:
        return request.extensions.get("request_name", request.url.path)

    @staticmethod
    def _elapsed_ms(request: Request) -> float:
        start_time = request.extensions.get("start_time", time.time())
        return (time.time() - start_time) * 1000
