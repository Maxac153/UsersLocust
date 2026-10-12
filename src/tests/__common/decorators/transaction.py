import time
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable, Generator

from locust import events
from locust.exception import (
    InterruptTaskSet,
    RescheduleTask,
    RescheduleTaskImmediately,
    StopTest,
    StopUser,
)

from src.tests.__common.models.locust_request_event.locust_request_event import LocustRequestEvent

# Locust ends a task with these on purpose: an interrupted transaction is neither a success nor a failure
CONTROL_FLOW_EXCEPTIONS = (StopUser, StopTest, InterruptTaskSet, RescheduleTask, RescheduleTaskImmediately)

# Greenlets have their own contextvars context, so concurrent users never share failures
_current_failures: ContextVar[list[BaseException] | None] = ContextVar("transaction_failures", default=None)


@events.request.add_listener
def _record_inner_failure(exception: BaseException | None = None, **_kwargs: Any) -> None:
    failures = _current_failures.get()
    if failures is not None and exception is not None:
        failures.append(exception)


@contextmanager
def _collect_failures() -> Generator[list[BaseException], None, None]:
    failures: list[BaseException] = []
    token = _current_failures.set(failures)
    try:
        yield failures
    finally:
        _current_failures.reset(token)


class Transaction:
    """Reports a task as one request; it fails if the task raises or any request inside it failed."""

    def __init__(self, transaction_name: str) -> None:
        self.transaction_name = transaction_name

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            with _collect_failures() as failures:
                try:
                    result = func(*args, **kwargs)
                except CONTROL_FLOW_EXCEPTIONS:
                    raise
                except Exception as error:
                    self._fire(start_time, error)
                    raise
            self._fire(start_time, failures[0] if failures else None)
            return result

        return wrapper

    def _fire(self, start_time: float, exception: BaseException | None) -> None:
        event = LocustRequestEvent(
            name=self.transaction_name,
            response_time=(time.perf_counter() - start_time) * 1000,
            exception=exception,
        )
        events.request.fire(**event.model_dump())
