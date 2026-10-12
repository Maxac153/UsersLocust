from locust import LoadTestShape

from src.tests.__common.models.stage.stage import Stage
from src.tests.__common.models.stage.stages_config import StagesConfig

DEFAULT_STAGES = (Stage(duration=60, users=1, spawn_rate=1),)


class StagesShape(LoadTestShape):
    """Plays --STAGES; import it into a scenario module so Locust discovers it there."""

    _stages: tuple[Stage, ...] | None = None

    def tick(self) -> tuple[int, float] | None:
        if self._stages is None:
            # Read from the runner's options, not from a User: on a distributed master no User ever exists
            self._stages = self.load_stages(self.runner.environment.parsed_options.STAGES)

        run_time = self.get_run_time()
        for stage in self._stages:
            if run_time < stage.duration:
                return stage.users, stage.spawn_rate
        return None

    @staticmethod
    def load_stages(stages_json: str | None) -> tuple[Stage, ...]:
        if stages_json is None:
            return DEFAULT_STAGES
        return tuple(StagesConfig.model_validate_json(stages_json).root)
