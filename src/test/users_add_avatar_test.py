import random

from locust import HttpUser, between, task
import os

from src.resources.config.common_config import cfg


class UserRegistration(HttpUser):
    wait_time = between(5, 5)
    host = cfg.api_host

    def on_start(self) -> None:
        self.query_params_reg = { "email": "manager@mail.ru" }
        self.dir_img = []

        root_dir = 'src/resources/img'
        for file in os.listdir(root_dir):
            self.dir_img.append(os.path.join(root_dir, file))


    @task
    def user_add_avatar(self):
        self.client.get("/")
        with open(random.choice(self.dir_img), 'rb') as img:
            self.client.post(
                "/tasks/rest/addavatar",
                name="/add_avatar",
                params=self.query_params_reg,
                files={"avatar": img}
            )
