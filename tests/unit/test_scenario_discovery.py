from pathlib import Path

import pytest
from locust.util.load_locustfile import load_locustfile

from src.tests.__common.shapes.stages_shape import StagesShape
from src.tests.__common.users.scenario_user import ScenarioUser

SCENARIOS = sorted(str(path) for path in Path("src/tests").glob("system_*/t*/*_scenario.py"))


def test_scenarios_are_found():
    assert SCENARIOS


@pytest.mark.parametrize("scenario_path", SCENARIOS)
def test_scenario_exposes_one_profile_driven_user_and_stages_shape(scenario_path):
    user_classes, shape_classes = load_locustfile(scenario_path)

    assert len(user_classes) == 1
    [user_class] = user_classes.values()
    assert issubclass(user_class, ScenarioUser)
    assert [type(shape) for shape in shape_classes] == [StagesShape]
