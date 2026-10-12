from locust import events, task

# import src.tests.__common.hooks.prometheus_hooks  # noqa F401
import src.tests.__common.hooks.influxdb2_hooks  # noqa F401
from src.tests.__common.decorators.transaction import Transaction
from src.tests.__common.shapes.stages_shape import StagesShape  # noqa: F401
from src.tests.__common.users.scenario_user import ScenarioUser


class KafkaSend(ScenarioUser):
    property_files = (
        "src/resources/properties/tests/system_fake_bank/t2_kafka/kafka_properties.json",
    )

    @task
    @Transaction("uc_fake_bank_1_kafka_send")
    def kafka_scenario(self) -> None:
        # Placeholder until a Kafka client exists: reports a zero-time send
        events.request.fire(
            request_type="KAFKA",
            name="ur_fake_bank_1.2_kafka_send_accounts",
            response_time=0,
            response_length=0,
            context=None,
            exception=None,
        )
