import json

from locust import task, constant_pacing, HttpUser, LoadTestShape

import src.tests.__common.helpers.add_arguments_helper  # noqa: F401
# import src.tests.__common.hooks.prometheus_hooks  # noqa F401
import src.tests.__common.hooks.influxdb2_hooks  # noqa F401
from src.tests.__common.clients.httpx_client import HttpClient
from src.tests.__common.decorators.transaction import Transaction
from src.tests.__common.helpers.property_helper import PropertyHelper
from src.tests.__common.models.stage.stages_config import StagesConfig

STAGES = [{"duration": 60, "users": 1, "spawn_rate": 1}]


class CreateUsers(HttpUser):
    host = "localhost"
    httpx_client = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        options = self.environment.parsed_options
        self.debug_enable = getattr(options, "DEBUG_ENABLE", True).strip().lower() == "true"
        self.__class__.wait_time = constant_pacing(getattr(options, "PACING", 1.0))
        stages_str = getattr(options, "STAGES", None)
        if stages_str is not None:
            StagesConfig.model_validate_json(stages_str)
            global STAGES
            STAGES = json.loads(stages_str)
        self.properties = PropertyHelper.read_properties(
            getattr(options, "PROPERTIES", None),
            "src/resources/properties/__common/common_properties.json",
            "src/resources/properties/tests/system_reqres/reqres.json",
            "src/resources/properties/tests/system_reqres/__groups/reqres_host.json",
            "src/resources/properties/tests/system_reqres/t1_create_users/create_users_properties.json"
        )

    def on_start(self) -> None:
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
    def tick(self) -> tuple[int, int] | None:
        run_time = self.get_run_time()
        for stage in STAGES:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]
        return None
