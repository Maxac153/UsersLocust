from locust import task

# import src.tests.__common.hooks.prometheus_hooks  # noqa F401
import src.tests.__common.hooks.influxdb2_hooks  # noqa F401
from src.tests.__common.decorators.transaction import Transaction
from src.tests.__common.shapes.stages_shape import StagesShape  # noqa: F401
from src.tests.__common.users.scenario_user import HttpScenarioUser


class GetAccounts(HttpScenarioUser):
    host_property = "FAKE_BANK_HOST"
    property_files = (
        "src/resources/properties/__common/common_properties.json",
        "src/resources/properties/tests/system_fake_bank/fake_bank.json",
        "src/resources/properties/tests/system_fake_bank/__groups/fake_bank_host.json",
        "src/resources/properties/tests/system_fake_bank/t1_get_accounts/get_accounts_properties.json",
    )

    @task
    @Transaction("uc_fake_bank_1_rest_get_accounts")
    def get_accounts_scenario(self) -> None:
        self.httpx_client.get(
            "/fakebank/accounts",
            extensions={"request_name": "ur_fake_bank_1.1_rest_get_/fakebank/accounts"},
        )
