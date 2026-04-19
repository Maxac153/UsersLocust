from locust import task, constant_pacing, HttpUser, LoadTestShape

import src.tests.__common.helpers.add_arguments_helper  # noqa: F401
# import src.tests.__common.hooks.prometheus_hooks  # noqa F401
import src.tests.__common.hooks.influxdb2_hooks  # noqa F401
from src.tests.__common.clients.httpx_client import HttpClient
from src.tests.__common.decorators.transaction import Transaction
from src.tests.__common.helpers.property_helper import PropertyHelper


class CreateUsers(HttpUser):
    host = "localhost"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        options = self.environment.parsed_options
        self.debug_enable = options.DEBUG_ENABLE.strip().lower() == "true"
        self.__class__.wait_time = constant_pacing(options.PACING)
        self.properties = PropertyHelper.read_properties(
            options.PROPERTIES,
            "src/resources/properties/__common/common_properties.json",
            "src/resources/properties/tests/system_reqres/reqres.json",
            "src/resources/properties/tests/system_reqres/__groups/reqres_host.json",
            "src/resources/properties/tests/system_reqres/t1_create_users/create_users_properties.json"
        )

        self.httpx_client = HttpClient(
            timeout=10.0,
            client_url=self.properties.get("REQRES_HOST"),
            environment=self.environment,
        )

    @task
    @Transaction("uc_reqres_1_create_users")
    def get_accounts_scenario(self) -> None:
        self.httpx_client.post(
            "/api/users",
            json={
                "name": "morpheus",
                "job": "leader"
            },
            extensions={"request_name": "ur_reqres_1.1_rest_post_create_users_/api/users"},
        )

        if self.debug_enable:
            self.environment.runner.quit()

    def on_stop(self) -> None:
        self.httpx_client.close()


class StagesShape(LoadTestShape):
    def tick(self) -> tuple[int, float] | None:
        for stage in self.stages:
            if self.get_run_time() < stage.duration:
                return stage.users, stage.spawn_rate
        return None
