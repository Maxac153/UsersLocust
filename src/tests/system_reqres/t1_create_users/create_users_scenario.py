from locust import task

# import src.tests.__common.hooks.prometheus_hooks  # noqa F401
import src.tests.__common.hooks.influxdb2_hooks  # noqa F401
from src.tests.__common.decorators.transaction import Transaction
from src.tests.__common.shapes.stages_shape import StagesShape  # noqa: F401
from src.tests.__common.users.scenario_user import HttpScenarioUser


class CreateUsers(HttpScenarioUser):
    host_property = "REQRES_HOST"
    property_files = (
        "src/resources/properties/__common/common_properties.json",
        "src/resources/properties/tests/system_reqres/reqres.json",
        "src/resources/properties/tests/system_reqres/__groups/reqres_host.json",
        "src/resources/properties/tests/system_reqres/t1_create_users/create_users_properties.json",
    )

    @task
    @Transaction("uc_reqres_1_create_users")
    def create_users_scenario(self) -> None:
        self.httpx_client.post(
            "/api/users",
            json={"name": "morpheus", "job": "leader"},
            extensions={"request_name": "ur_reqres_1.1_rest_post_create_users_/api/users"},
        )
