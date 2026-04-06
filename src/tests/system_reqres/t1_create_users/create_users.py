from locust import task, constant_pacing, HttpUser, LoadTestShape

from src.tests.__common.decorators.transaction import transaction
from src.tests.__common.helpers.logger_helper import LogConfig


class Accounts(HttpUser):
    host = "https://reqres.in"
    wait_time = constant_pacing(2)

    def __init__(self, environment) -> None:
        super().__init__(environment)
        self.profile = None
        self.properties = None

    def on_start(self) -> None:
        pass
        # self.properties = PropertyHelper.read_properties(
        #     None,
        #     "src/resources/__common/common_properties.json",
        #     "src/resources/tests/system_reqres/system_fake_bank.json",
        #     "src/resources/tests/system_reqres/__groups/reqres_host.json",
        #     "src/resources/tests/system_reqres/t1_create_users/create_users_properties.json"
        # )
        # self.profile = {}
        # self.wait_time = constant_pacing(self.profile.get("PACING"))
        # self.host = self.properties.get("PORT") + "://" + self.properties.get("HOST")

    @task
    @transaction("uc_reqres_1_create_users")
    def create_users(self) -> None | Exception:
        with self.client.post(
                catch_response=True,
                name="ur_reqres_1_rest_post_create_users",
                url="/api/users",
                json={
                    "name": "morpheus",
                    "job": "leader"
                }
        ) as request:
            LogConfig.logger.debug(request.status_code)
            if not (200 <= request.status_code <= 299):
                return Exception("Transaction Error")

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
