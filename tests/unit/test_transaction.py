import gevent
import pytest
from locust import events
from locust.exception import StopUser

from src.tests.__common.decorators.transaction import Transaction


def fire_inner_request(exception=None):
    events.request.fire(
        request_type="HTTP", name="ur_inner", response_time=1, response_length=0, exception=exception,
    )


def transactions(fired):
    return [event for event in fired if event["request_type"] == "TRANSACTION"]


def test_successful_task_reports_success(fired_requests):
    @Transaction("uc_ok")
    def task():
        fire_inner_request()
        return "result"

    assert task() == "result"
    [transaction] = transactions(fired_requests)
    assert transaction["name"] == "uc_ok"
    assert transaction["exception"] is None
    assert transaction["response_time"] >= 0


def test_failed_inner_request_fails_transaction(fired_requests):
    inner_error = RuntimeError("500 Internal Server Error")

    @Transaction("uc_inner_failed")
    def task():
        fire_inner_request(exception=inner_error)
        fire_inner_request()

    task()

    [transaction] = transactions(fired_requests)
    assert transaction["exception"] is inner_error


def test_raised_exception_fails_transaction_and_propagates(fired_requests):
    @Transaction("uc_raised")
    def task():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        task()

    [transaction] = transactions(fired_requests)
    assert isinstance(transaction["exception"], ValueError)


def test_return_value_is_not_treated_as_exception(fired_requests):
    @Transaction("uc_returns_value")
    def task():
        return RuntimeError("not an error, just a value")

    task()

    [transaction] = transactions(fired_requests)
    assert transaction["exception"] is None


def test_control_flow_exception_is_not_reported(fired_requests):
    @Transaction("uc_stopped")
    def task():
        raise StopUser()

    with pytest.raises(StopUser):
        task()

    assert transactions(fired_requests) == []


def test_nested_failure_fails_outer_transaction(fired_requests):
    inner_error = RuntimeError("inner")

    @Transaction("uc_inner")
    def inner():
        fire_inner_request(exception=inner_error)

    @Transaction("uc_outer")
    def outer():
        inner()

    outer()

    by_name = {event["name"]: event for event in transactions(fired_requests)}
    assert by_name["uc_inner"]["exception"] is inner_error
    assert by_name["uc_outer"]["exception"] is inner_error


def test_failures_do_not_leak_between_greenlets(fired_requests):
    @Transaction("uc_failing_user")
    def failing_user():
        gevent.sleep(0.01)
        fire_inner_request(exception=RuntimeError("only mine"))
        gevent.sleep(0.02)

    @Transaction("uc_healthy_user")
    def healthy_user():
        gevent.sleep(0.02)
        fire_inner_request()

    gevent.joinall([gevent.spawn(failing_user), gevent.spawn(healthy_user)], raise_error=True)

    by_name = {event["name"]: event for event in transactions(fired_requests)}
    assert by_name["uc_healthy_user"]["exception"] is None
    assert by_name["uc_failing_user"]["exception"] is not None


def test_no_transaction_context_outside_decorator(fired_requests):
    fire_inner_request(exception=RuntimeError("standalone"))

    assert transactions(fired_requests) == []
