from locust import events, LoadTestShape

from src.tests.__common.models.stage.stage import Stage
from src.tests.__common.models.stage.stages_config import StagesConfig


@events.init_command_line_parser.add_listener
def add_arguments(parser) -> None:
    parser.add_argument("--DEBUG_ENABLE", type=str, env_var="DEBUG_ENABLE", default="true", help="Debug Ture, False")
    parser.add_argument("--PACING", type=float, env_var="PACING", default=1.0, help="Delay between requests")
    parser.add_argument("--STAGES", type=str, env_var="STAGES", default=None, help="JSON of load stages")
    parser.add_argument("--PROPERTIES", type=str, env_var="PROPERTIES", default=None, help="Properties for the test")


@events.init.add_listener
def init_shape_profile(environment, **_kwargs) -> None:
    stages_str = environment.parsed_options.STAGES
    if stages_str is not None:
        LoadTestShape.stages = StagesConfig.model_validate_json(stages_str).root
    else:
        LoadTestShape.stages = [Stage(duration=60, users=1, spawn_rate=1)]
