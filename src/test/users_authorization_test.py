import json
import random

from locust import HttpUser, task, LoadTestShape, constant_pacing

from src.resources.config.common_config import cfg
from src.test.data_structure.authorization import Authorization
from src.test.helpers.csv_reader import CsvReader


class StagesShape(LoadTestShape):
    with open("src/resources/profile/authorization.json") as p:
        stages = json.load(p)

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data
        return None


class UsersAuthorization(HttpUser):
    wait_time = constant_pacing(cfg.pacing_sec)
    host = cfg.api_host

    def on_start(self) -> None:
        self.csv_data = CsvReader("src/resources/data/aut_users.csv").read_data_csv()

    @task
    def user_authorization(self) -> None:
        self.client.get(
            "/",
            name="/main_page"
        )

        login, password = random.choice(self.csv_data)
        self.client.post(
            "/user/login/index.html",
            params=Authorization.data_user_json(login, password),
            name="/authorization"
        )

        self.client.get(
            "/",
            name="/main_page"
        )

        self.client.get(
            "/user/logout.html",
            name="/logout"
        )

        self.client.get(
            "/",
            name="/main_page"
        )
