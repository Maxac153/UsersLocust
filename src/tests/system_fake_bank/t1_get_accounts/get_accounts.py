import time

from locust import task, constant_pacing, HttpUser, LoadTestShape, events

from src.tests.__common.helpers.config import cfg, logger


class Accounts(HttpUser):
    wait_time = constant_pacing(1.0)
    host = cfg.api_host

    def on_start(self) -> None:
        pass

    @task
    def get_accounts(self) -> None:
        start_time = time.time()

        with self.client.get(
                "/fakebank/accounts",
                catch_response=True,
                name="ur_fake_bank_1.1_rest_get_accounts"
        ) as request:
            logger.info(request.status_code)

        # Замер времени выполнения операции
        # request_start_time = time.time()
        # Отправка сообщения
        # processing_time = int((time.time() - request_start_time) * 1000)
        events.request.fire(
            request_type="KAFKA",
            name="ur_fake_bank_1.2_kafka_send_accounts",
            response_time=100,
            response_length=0,
            context=None,
            exception=None,
        )

        total_time = int((time.time() - start_time) * 1000)
        events.request.fire(
            request_type="TRANSACTION",
            name="uc_fake_bank_1_accounts",
            response_time=total_time,
            response_length=0,
            exception=None
        )


def on_stop(self) -> None:
    pass


class StagesShape(LoadTestShape):
    stages = [
        {"duration": 10, "users": 1, "spawn_rate": 1},
        {"duration": 20, "users": 2, "spawn_rate": 1}
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data
        return None
