import time
from functools import wraps

from locust import HttpUser, between, task, events

from src.resources.config.common_config import cfg
from src.test.data_structure.registration import Registration

def proceed_request(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        request_start_time = time.time()
        transaction = func(*args, **kwargs)
        processing_time = int((time.time() - request_start_time) * 1000)

        if func.__name__ == "user_registration":
            events.request.fire(
                request_type="LOCUST_INFLUXDB",
                name=func.__name__,
                response_time=processing_time,
                response_length=0,
                context=None,
                exception=None,
            )
        else:
            processing_time = int(transaction.elapsed.total_seconds() * 1000)

        cfg.influxdb.write(
            cfg.influx_bucket,
            cfg.influx_org,
            [{
                "measurement": "locust",
                "tags": {"transaction_name": func.__name__},
                "time": time.time_ns(),
                "fields": {"response_time": processing_time},
            }],
        )

    return wrapper

class UserRegistration(HttpUser):
    wait_time = between(5, 5)
    host = cfg.api_host

    @task
    @proceed_request
    def user_registration(self):
        self.client.get(
            "/",
            name="/main_page"
        )

        self.client.post(
            "/tasks/rest/doregister",
            name="/registration",
            json=Registration.random_reg_user()
        )

        self.client.get(
            "/",
            name="/main_page"
        )

        self.client.get(
            "/user/logout.html",
            name="/logout"
        )

        self.client.get(
            "/",
            name="/main_page"
        )
