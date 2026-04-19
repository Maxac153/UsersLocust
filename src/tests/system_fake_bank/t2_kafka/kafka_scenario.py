from locust import task, HttpUser, LoadTestShape, events, constant_pacing

import src.tests.__common.helpers.add_arguments_helper  # noqa: F401
# import src.tests.__common.hooks.prometheus_hooks  # noqa F401
import src.tests.__common.hooks.influxdb2_hooks  # noqa F401
from src.tests.__common.decorators.transaction import Transaction
from src.tests.__common.helpers.property_helper import PropertyHelper


class KafkaSend(HttpUser):
    host = "localhost"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        options = self.environment.parsed_options
        self.debug_enable = options.DEBUG_ENABLE.strip().lower() == "true"
        self.__class__.wait_time = constant_pacing(options.PACING)
        self.properties = PropertyHelper.read_properties(
            options.PROPERTIES,
            "src/resources/properties/tests/system_fake_bank/t2_kafka/kafka_properties.json"
        )

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


class StagesShape(LoadTestShape):
    def tick(self) -> tuple[int, float] | None:
        for stage in self.stages:
            if self.get_run_time() < stage.duration:
                return stage.users, stage.spawn_rate
        return None
