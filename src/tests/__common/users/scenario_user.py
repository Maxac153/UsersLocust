from locust import User, constant_pacing

import src.tests.__common.helpers.add_arguments_helper  # noqa: F401
from src.tests.__common.clients.httpx_client import HttpClient
from src.tests.__common.helpers.property_helper import PropertyHelper


class ScenarioUser(User):
    """Base for profile-driven scenarios: pacing, properties and debug mode come from the runner's CLI args."""

    abstract = True
    property_files: tuple[str, ...] = ()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        options = self.environment.parsed_options
        self.debug_enable: bool = options.DEBUG_ENABLE
        self._pacing_wait = constant_pacing(options.PACING)
        self.properties = PropertyHelper.read_properties(options.PROPERTIES, *self.property_files)

    def wait_time(self) -> float:
        # Locust waits only after a task finishes, so quitting here keeps the iteration's
        # @Transaction event; quitting inside the task killed the greenlet before it fired
        if self.debug_enable:
            self.environment.runner.quit()
        return self._pacing_wait(self)


class HttpScenarioUser(ScenarioUser):
    abstract = True
    host_property: str = ""
    http_timeout: float = 10.0

    def on_start(self) -> None:
        self.httpx_client = HttpClient(
            timeout=self.http_timeout,
            client_url=self.properties[self.host_property],
            environment=self.environment,
        )

    def on_stop(self) -> None:
        self.httpx_client.close()
