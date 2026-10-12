from locust import LoadTestShape, events

from src.tests.__common.models.stage.stage import Stage
from src.tests.__common.models.stage.stages_config import StagesConfig

DEFAULT_STAGES = (Stage(duration=60, users=1, spawn_rate=1),)


class StagesShape(LoadTestShape):
    """Plays --STAGES; import it into a scenario module so Locust discovers it there."""

    stages: tuple[Stage, ...] = DEFAULT_STAGES

    def tick(self) -> tuple[int, float] | None:
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage.duration:
                return stage.users, stage.spawn_rate
        return None

    @staticmethod
    def load_stages(stages_json: str | None) -> tuple[Stage, ...]:
        if stages_json is None:
            return DEFAULT_STAGES
        return tuple(StagesConfig.model_validate_json(stages_json).root)


@events.init.add_listener
def load_stages_on_init(environment, **_kwargs) -> None:
    # init fires once per process before the test starts (also on a distributed master, which has no Users),
    # so invalid --STAGES fails at startup instead of inside the running shape greenlet
    if isinstance(environment.shape_class, StagesShape):
        environment.shape_class.stages = StagesShape.load_stages(environment.parsed_options.STAGES)
