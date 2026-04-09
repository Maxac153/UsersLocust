import time
from functools import wraps
from typing import Callable, Any

from locust import events

from src.tests.__common.models.locust_request_event.locust_request_event import LocustRequestEvent


def transaction(transaction_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Декоратор для транзакций"""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            result = func(*args, **kwargs)
            event_data = LocustRequestEvent(
                name=transaction_name,
                response_time=int((time.time() - start_time) * 1000),
                exception=result
            )
            events.request.fire(**event_data.model_dump())
            return result

        return wrapper

    return decorator
