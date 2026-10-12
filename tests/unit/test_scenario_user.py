import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from locust import events
from locust.env import Environment

from src.tests.__common.users.scenario_user import HttpScenarioUser, ScenarioUser


class PlainUser(ScenarioUser):
    abstract = True


class HttpUserUnderTest(HttpScenarioUser):
    abstract = True
    host_property = "TEST_HOST"


def make_environment(debug_enable=False, pacing=5.0, properties=None) -> Environment:
    environment = Environment(events=events)
    environment.parsed_options = Namespace(
        DEBUG_ENABLE=debug_enable,
        PACING=pacing,
        STAGES=None,
        PROPERTIES=json.dumps(properties) if properties is not None else None,
    )
    environment.runner = MagicMock()
    return environment


def test_reads_properties_from_files_then_cli(tmp_path: Path):
    properties_file = tmp_path / "test.json"
    properties_file.write_text(json.dumps({"FROM_FILE": "1", "OVERRIDDEN": "file"}))

    class User(PlainUser):
        property_files = (str(properties_file),)

    user = User(make_environment(properties={"OVERRIDDEN": "cli"}))

    assert user.properties == {"FROM_FILE": "1", "OVERRIDDEN": "cli"}


def test_wait_time_applies_constant_pacing():
    user = PlainUser(make_environment(pacing=5.0))

    assert user.wait_time() == pytest.approx(5.0, abs=0.1)


def test_debug_quits_after_iteration_not_during_it():
    environment = make_environment(debug_enable=True)
    user = PlainUser(environment)
    environment.runner.quit.assert_not_called()

    user.wait_time()

    environment.runner.quit.assert_called_once()


def test_regular_run_does_not_quit():
    environment = make_environment(debug_enable=False)

    PlainUser(environment).wait_time()

    environment.runner.quit.assert_not_called()


def test_http_user_builds_client_from_host_property():
    user = HttpUserUnderTest(make_environment(properties={"TEST_HOST": "http://test.local"}))

    user.on_start()

    assert str(user.httpx_client.client.base_url) == "http://test.local"
    user.on_stop()
    assert user.httpx_client.client.is_closed


def test_http_user_fails_loudly_without_host_property():
    user = HttpUserUnderTest(make_environment(properties={}))

    with pytest.raises(KeyError, match="TEST_HOST"):
        user.on_start()
