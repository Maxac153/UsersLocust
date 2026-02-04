import time
from functools import wraps
from typing import Callable, Any

from locust import events


def transaction(transaction_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            result = func(*args, **kwargs)
            events.request.fire(
                request_type="TRANSACTION",
                name=transaction_name,
                response_time=int((time.time() - start_time) * 1000),
                response_length=0,
                exception=result,
            )

        return wrapper

    return decorator
