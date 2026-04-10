import json

from locust import task, HttpUser, LoadTestShape, events, constant_pacing

import src.tests.__common.helpers.add_arguments_helper  # noqa: F401
import src.tests.__common.hooks.prometheus_hooks  # noqa F401
from src.tests.__common.decorators.transaction import Transaction
from src.tests.__common.helpers.property_helper import PropertyHelper
from src.tests.__common.models.stage.stages_config import StagesConfig

STAGES = [{"duration": 60, "users": 1, "spawn_rate": 1}]


class KafkaSend(HttpUser):
    host = "localhost"

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
            "src/resources/properties/tests/system_fake_bank/t2_kafka/kafka_properties.json"
        )

    def on_start(self) -> None:
        pass

    @task
    @Transaction("uc_fake_bank_1_kafka_send")
    def kafka_scenario(self) -> Exception | None:
        events.request.fire(
            request_type="KAFKA",
            name="ur_fake_bank_1.2_kafka_send_accounts",
            response_time=0,
            response_length=0,
            context=None,
            exception=None,
        )

        if self.debug_enable:
            self.environment.runner.quit()

    def on_stop(self) -> None:
        pass


class StagesShape(LoadTestShape):
    def tick(self) -> tuple[int, int] | None:
        run_time = self.get_run_time()
        for stage in STAGES:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]
        return None
