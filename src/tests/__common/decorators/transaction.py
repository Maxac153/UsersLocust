import time
from functools import wraps
from typing import Callable, Any

from locust import events

from src.tests.__common.models.locust_request_event.locust_request_event import LocustRequestEvent


class Transaction:
    def __init__(self, transaction_name: str):
        self.transaction_name = transaction_name

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            result = func(*args, **kwargs)
            response_time = int((time.time() - start_time) * 1000)

            event_data = LocustRequestEvent(
                name=self.transaction_name,
                response_time=response_time,
                exception=result
            )
            events.request.fire(**event_data.model_dump())
            return result

        return wrapper
