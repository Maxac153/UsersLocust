from locust import events

from src.tests.__common.helpers.cli_helper import str_to_bool


@events.init_command_line_parser.add_listener
def add_arguments(parser) -> None:
    parser.add_argument("--DEBUG_ENABLE", type=str_to_bool, env_var="DEBUG_ENABLE", default=True, help="Debug true, false")
    parser.add_argument("--PACING", type=float, env_var="PACING", default=1.0, help="Delay between requests")
    parser.add_argument("--STAGES", type=str, env_var="STAGES", default=None, help="JSON of load stages")
    parser.add_argument("--PROPERTIES", type=str, env_var="PROPERTIES", default=None, help="Properties for the test")
