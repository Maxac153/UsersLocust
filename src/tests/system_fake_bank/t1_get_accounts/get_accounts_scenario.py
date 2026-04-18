from locust import HttpUser, LoadTestShape, constant_pacing, task

import src.tests.__common.helpers.add_arguments_helper  # noqa: F401

# import src.tests.__common.hooks.prometheus_hooks  # noqa F401
import src.tests.__common.hooks.influxdb2_hooks  # noqa F401
from src.tests.__common.clients.httpx_client import HttpClient
from src.tests.__common.decorators.transaction import Transaction
from src.tests.__common.helpers.property_helper import PropertyHelper
from src.tests.__common.models.stage.stages_config import StagesConfig
from src.tests.__common.models.stage.stage import Stage

DEFAULT_STAGES = [Stage(duration=60, users=1, spawn_rate=1)]

FILES = (
    "src/resources/properties/__common/common_properties.json",
    "src/resources/properties/tests/system_fake_bank/fake_bank.json",
    "src/resources/properties/tests/system_fake_bank/__groups/fake_bank_host.json",
    "src/resources/properties/tests/system_fake_bank/t1_get_accounts/get_accounts_properties.json",
)


class GetAccounts(HttpUser):
    host = "localhost"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        options = self.environment.parsed_options
        self.debug_enable = bool(options.DEBUG_ENABLE)
        self.wait_time = constant_pacing(options.PACING)

        self.properties = PropertyHelper.read_properties(
            options.PROPERTIES,
            *FILES,
        )

    def on_start(self) -> None:
        self.httpx_client = HttpClient(
            timeout=10.0,
            client_url=self.properties.get("FAKE_BANK_HOST"),
            environment=self.environment,
        )

    @task
    @Transaction("uc_fake_bank_1_rest_get_accounts")
    def get_accounts_scenario(self) -> None:
        self.httpx_client.get(
            "/fakebank/accounts",
            extensions={"request_name": "ur_fake_bank_1.1_rest_get_/fakebank/accounts"},
        )

        if self.debug_enable:
            self.environment.runner.quit()

    def on_stop(self) -> None:
        self.httpx_client.close()


class StagesShape(LoadTestShape):
    _stages: list[Stage] | None = None

    def tick(self) -> tuple[int, float] | None:
        if self._stages is None:
            self._stages = self._load_stages()
        print(self._stages)

        run_time = self.get_run_time()

        for stage in self._stages:
            if run_time < stage.duration:
                return stage.users, stage.spawn_rate
        return None

    def _load_stages(self) -> list[Stage]:
        stages_str = self.runner.environment.parsed_options.STAGES
        if stages_str is not None:
            return StagesConfig.model_validate_json(stages_str).root
        return DEFAULT_STAGES
