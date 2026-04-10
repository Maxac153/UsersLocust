import time

from httpx import Request, Response, HTTPStatusError, HTTPError
from locust.env import Environment


class EventHooks:
    @staticmethod
    def locust_request_event_hook(request: Request) -> None:
        request.extensions["start_time"] = time.time()

    @staticmethod
    def locust_response_event_hook(environment: Environment):
        def inner(response: Response) -> None:
            exception: HTTPError | HTTPStatusError | None = None

            try:
                response.raise_for_status()
            except (HTTPError, HTTPStatusError) as error:
                exception = error

            request = response.request
            request_name = request.extensions.get("request_name", request.url.path)
            start_time = request.extensions.get("start_time", time.time())
            response_time = (time.time() - start_time) * 1000
            response_length = len(response.read())
            environment.events.request.fire(
                request_type="HTTP",
                name=request_name,
                response_time=response_time,
                response_length=response_length,
                response=response,
                exception=exception,
                context=None
            )

        return inner
