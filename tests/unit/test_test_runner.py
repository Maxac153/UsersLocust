import json
import logging
import sys
from pathlib import Path

import pytest

# Aliased: pytest would try to collect a module-level name starting with "Test"
from src.tests.__common.models.profile.tests_param import TestsParam as ProfileModel
from src.tests.test_runner import (
    EXIT_FAILED,
    EXIT_OK,
    LocustCommandBuilder,
    LocustRun,
    ParallelLocustRunner,
    apply_percent_profile,
)

LOGGER = logging.getLogger("test_runner_tests")


def element(test_path: str, scenarios: dict, properties: dict, env: list[str] | None = None) -> dict:
    return {
        "X": 0,
        "Y": 0,
        "PROFILE": {
            "RUN": {"ENV": ["input/env/redis/redis.json"] if env is None else env, "LOAD_GENERATOR": "localhost", "TEST_PATH": test_path},
            "PROFILE": scenarios,
            "PROPERTIES": properties,
        },
    }


def scenario(pacing: float = 10, tps: float = 0.5) -> dict:
    return {"PACING": pacing, "STEPS": [{"TPS": tps, "RAMP_TIME": 1, "HOLD_TIME": 1}]}


def make_profiles(elements: dict, common_properties: dict | None = None, percent: float = 1.0) -> ProfileModel:
    return ProfileModel.model_validate({
        "ELEMENTS": elements,
        "CONNECTIONS": [],
        "FORM": {"X": 0, "Y": 0, "WIDTH": 1, "HEIGHT": 1},
        "COMMON_SETTINGS": {
            "RUN_SETTINGS": {
                "DATASOURCE_URL": "http://localhost:8086", "INFLUX_BUCKET": "metrics", "INFLUX_ORG": "monitoring",
                "PROMETHEUS_PORT": "9646", "PROFILE_NAME": "test", "SYSTEM_NAME": "test",
                "PERCENT_PROFILE": percent, "LOG_LEVEL": "INFO",
            },
            "PROPERTIES": common_properties or {},
        },
    })


def option(command: list[str], name: str) -> str:
    if name in command:
        return command[command.index(name) + 1]
    prefix = f"{name}="
    return next(arg[len(prefix):] for arg in command if arg.startswith(prefix))


def builder(profiles: ProfileModel, tmp_path: Path, debug_enable: bool = False) -> LocustCommandBuilder:
    return LocustCommandBuilder(profiles, debug_enable=debug_enable, output_dir=tmp_path, logger=LOGGER)


class TestMergeProperties:
    def test_test_properties_override_common(self, tmp_path):
        profiles = make_profiles(
            {"t1": element("t1.py", {"S1": scenario()}, {"HOST": "test-host"})},
            common_properties={"HOST": "common-host", "COMMON_ONLY": "1"},
        )

        [run] = builder(profiles, tmp_path).build_all()

        properties = json.loads(option(run.command, "--PROPERTIES"))
        assert properties["HOST"] == "test-host"
        assert properties["COMMON_ONLY"] == "1"

    def test_run_env_is_passed_to_property_helper(self, tmp_path):
        profiles = make_profiles({"t1": element("t1.py", {"S1": scenario()}, {}, env=["a.json", "b.json"])})

        [run] = builder(profiles, tmp_path).build_all()

        assert json.loads(option(run.command, "--PROPERTIES"))["ENV"] == ["a.json", "b.json"]

    def test_empty_run_env_is_omitted(self, tmp_path):
        profiles = make_profiles({"t1": element("t1.py", {"S1": scenario()}, {}, env=[])})

        [run] = builder(profiles, tmp_path).build_all()

        assert "ENV" not in json.loads(option(run.command, "--PROPERTIES"))

    def test_profile_model_is_not_mutated(self, tmp_path):
        profiles = make_profiles(
            {"t1": element("t1.py", {"S1": scenario(), "S2": scenario()}, {"OWN": "1"})},
            common_properties={"COMMON": "1"},
        )

        builder(profiles, tmp_path).build_all()

        assert profiles.ELEMENTS["t1"].PROFILE.PROPERTIES == {"OWN": "1"}


class TestOutputPaths:
    def test_every_scenario_gets_its_own_log_and_csv(self, tmp_path):
        profiles = make_profiles({
            "t1": element("t1.py", {"S1": scenario(), "S2": scenario()}, {}),
            "t2": element("t2.py", {"S1": scenario()}, {}),
        })

        runs = builder(profiles, tmp_path).build_all()

        log_files = [option(run.command, "--logfile") for run in runs]
        csv_prefixes = [option(run.command, "--csv") for run in runs]
        assert len(set(log_files)) == len(runs) == 3
        assert len(set(csv_prefixes)) == len(runs)
        assert str(tmp_path / "t1" / "S2.log") in log_files
        assert str(tmp_path / "t2" / "csv" / "S1") in csv_prefixes


class TestCommand:
    def test_debug_flag_and_stages(self, tmp_path):
        profiles = make_profiles({"t1": element("t1.py", {"S1": scenario(pacing=10, tps=0.5)}, {})})

        [run] = builder(profiles, tmp_path, debug_enable=False).build_all()

        assert run.run_id == "t1/S1"
        assert option(run.command, "-f") == "t1.py"
        assert option(run.command, "--DEBUG_ENABLE") == "false"
        assert json.loads(option(run.command, "--STAGES")) == [
            {"duration": 120, "users": 5, "spawn_rate": pytest.approx(5 / 60)},
        ]


def test_apply_percent_profile_scales_tps():
    profiles = make_profiles({"t1": element("t1.py", {"S1": scenario(tps=2.0)}, {})}, percent=0.5)

    apply_percent_profile(profiles)

    assert profiles.ELEMENTS["t1"].PROFILE.PROFILE["S1"].STEPS[0].TPS == 1.0


def test_percent_profile_must_be_positive():
    with pytest.raises(ValueError):
        make_profiles({"t1": element("t1.py", {"S1": scenario()}, {})}, percent=0)


# conftest imports locust, which lets gevent patch os.fork; the runner itself never imports locust
@pytest.mark.filterwarnings("ignore:This process .* is multi-threaded:DeprecationWarning")
class TestExitCode:
    def python_run(self, tmp_path: Path, run_id: str, exit_code: int) -> LocustRun:
        return LocustRun(
            run_id=run_id,
            command=[sys.executable, "-c", f"print('{run_id}'); raise SystemExit({exit_code})"],
            output_dir=tmp_path / run_id,
        )

    def runner(self, tmp_path, monkeypatch) -> ParallelLocustRunner:
        monkeypatch.chdir(tmp_path)
        profiles = make_profiles({"t1": element("t1.py", {"S1": scenario()}, {})})
        return ParallelLocustRunner(profiles, False, "2026-01-01", "2026-01-01_00-00-00")

    def test_all_succeeded(self, tmp_path, monkeypatch):
        runner = self.runner(tmp_path, monkeypatch)

        code = runner.run_all([self.python_run(tmp_path, "ok1", 0), self.python_run(tmp_path, "ok2", 0)])

        assert code == EXIT_OK

    def test_any_failed_process_fails_the_run(self, tmp_path, monkeypatch):
        runner = self.runner(tmp_path, monkeypatch)

        code = runner.run_all([self.python_run(tmp_path, "ok", 0), self.python_run(tmp_path, "bad", 1)])

        assert code == EXIT_FAILED

    def test_process_that_cannot_start_fails_the_run(self, tmp_path, monkeypatch):
        runner = self.runner(tmp_path, monkeypatch)
        missing = LocustRun(run_id="missing", command=["/nonexistent/binary"], output_dir=tmp_path / "missing")

        code = runner.run_all([self.python_run(tmp_path, "ok", 0), missing])

        assert code == EXIT_FAILED
