import argparse
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from logging import Logger
from pathlib import Path

from src.tests.__common.helpers.cli_helper import bool_to_cli, str_to_bool
from src.tests.__common.helpers.logger_helper import LoggerHelper
from src.tests.__common.helpers.profile_helper import ProfileHelper
from src.tests.__common.helpers.profile_log_helper import ProfileLogHelper
from src.tests.__common.models.profile.element import Element
from src.tests.__common.models.profile.scenario import Scenario
from src.tests.__common.models.profile.tests_param import TestsParam
from src.tests.__common.models.stage.stages_config import StagesConfig

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_INTERRUPTED = 130
TERMINATE_TIMEOUT_SECONDS = 10
MONITOR_INTERVAL_SECONDS = 10
# Load generators share the host with the runner: lower priority keeps the runner and log readers responsive
LOW_PRIORITY_PREFIX = ["nice", "-n", "10"] if os.name == "posix" else []


@dataclass(frozen=True)
class LocustRun:
    run_id: str
    command: list[str]
    output_dir: Path


@dataclass
class StartedRun:
    run: LocustRun
    process: subprocess.Popen


class LocustCommandBuilder:
    def __init__(self, profiles: TestsParam, debug_enable: bool, output_dir: Path, logger: Logger) -> None:
        self.profiles = profiles
        self.debug_enable = debug_enable
        self.output_dir = output_dir
        self.logger = logger

    def build_all(self) -> list[LocustRun]:
        return [
            self.build(test_name, element, scenario_name)
            for test_name, element in self.profiles.elements.items()
            for scenario_name in element.profile.PROFILE
        ]

    def build(self, test_name: str, element: Element, scenario_name: str) -> LocustRun:
        run_id = f"{test_name}/{scenario_name}"
        scenario = element.profile.PROFILE[scenario_name]
        plan = ProfileHelper.close_profile(scenario, self.debug_enable)
        self.warn_tps_deviations(run_id, scenario, plan.pacing)

        output_dir = self.output_dir / test_name
        command = [
            *LOW_PRIORITY_PREFIX,
            "locust", "-f", element.profile.RUN.TEST_PATH,
            f"--DEBUG_ENABLE={bool_to_cli(self.debug_enable)}",
            f"--PACING={plan.pacing}",
            f"--STAGES={StagesConfig(plan.stages).model_dump_json()}",
            f"--PROPERTIES={json.dumps(self.merge_properties(element))}",
            "--host=localhost",
            "--headless",
            "--logfile", str(output_dir / f"{scenario_name}.log"),
            "--csv", str(output_dir / "csv" / scenario_name),
            "--csv-full-history",
        ]
        return LocustRun(run_id=run_id, command=command, output_dir=output_dir)

    def merge_properties(self, element: Element) -> dict[str, str]:
        # Common properties are defaults: anything set on the test itself must win
        env_properties = {"ENV": element.profile.RUN.ENV} if element.profile.RUN.ENV else {}
        return {
            **self.profiles.COMMON_SETTINGS.PROPERTIES,
            **env_properties,
            **element.profile.PROPERTIES,
        }

    def warn_tps_deviations(self, run_id: str, scenario: Scenario, pacing: float) -> None:
        if self.debug_enable:
            return
        for deviation in ProfileHelper.tps_deviations(scenario, pacing):
            self.logger.warning(
                "%s Step #%d: Target TPS %.3f, Actual TPS %.3f (%+.1f%%) Due To Users Rounding At Pacing %.2fs",
                run_id, deviation.step_number, deviation.target_tps,
                deviation.actual_tps, deviation.percent, pacing,
            )


class ParallelLocustRunner:
    def __init__(
            self,
            profiles: TestsParam,
            debug_enable: bool,
            date_now_str: str,
            date_time_now_str: str,
    ) -> None:
        run_settings = profiles.COMMON_SETTINGS.RUN_SETTINGS
        os.environ["DATASOURCE_URL"] = run_settings.DATASOURCE_URL
        os.environ["INFLUX_BUCKET"] = run_settings.INFLUX_BUCKET
        os.environ["INFLUX_ORG"] = run_settings.INFLUX_ORG
        os.environ["PROMETHEUS_PORT"] = run_settings.PROMETHEUS_PORT
        os.environ["LOG_LEVEL"] = run_settings.LOG_LEVEL
        self.logger = LoggerHelper.setup_logger(date_now=date_now_str, date_time_now=date_time_now_str)
        self.builder = LocustCommandBuilder(
            profiles=profiles,
            debug_enable=debug_enable,
            output_dir=Path("output", "logs", date_now_str, date_time_now_str),
            logger=self.logger,
        )
        self.started_lock = threading.Lock()
        self.started: list[StartedRun] = []

    def run(self) -> int:
        return self.run_all(self.builder.build_all())

    def run_all(self, runs: list[LocustRun]) -> int:
        try:
            failed_to_start = self.start_all(runs)
            self.start_monitor()
            exit_codes = self.wait_all()
        except KeyboardInterrupt:
            self.logger.warning("🛑 Ctrl+C - Terminating All Processes...")
            self.terminate_all()
            return EXIT_INTERRUPTED
        return self.summarize(exit_codes, failed_to_start)

    def start_all(self, runs: list[LocustRun]) -> int:
        failed_to_start = sum(1 for run in runs if not self.start(run))
        self.logger.info("✅ Started %d Of %d Locust Tests In Parallel", len(runs) - failed_to_start, len(runs))
        return failed_to_start

    def start(self, run: LocustRun) -> bool:
        try:
            run.output_dir.joinpath("csv").mkdir(parents=True, exist_ok=True)
            process = subprocess.Popen(
                run.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as error:
            self.logger.error("Failed To Start [%s]: %s", run.run_id, error)
            return False

        self.logger.info("🚀 [%s] Started (PID: %s)", run.run_id, process.pid)
        threading.Thread(target=self.log_reader, args=(process, run.run_id), daemon=True).start()
        with self.started_lock:
            self.started.append(StartedRun(run=run, process=process))
        return True

    def log_reader(self, process: subprocess.Popen, run_id: str) -> None:
        try:
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.logger.debug("[%s] %s", run_id, line.rstrip())
        except (OSError, ValueError) as error:
            self.logger.exception("Failed To Read Logs From %s: %s", run_id, error)

    def start_monitor(self) -> None:
        threading.Thread(target=self.monitor_status, name="  Monitor ", daemon=True).start()

    def monitor_status(self) -> None:
        while True:
            with self.started_lock:
                total = len(self.started)
                running = sum(1 for started in self.started if started.process.poll() is None)
            if running == 0:
                return
            self.logger.info("⏱️ Running: %d | Finished: %d | Total: %d", running, total - running, total)
            time.sleep(MONITOR_INTERVAL_SECONDS)

    def wait_all(self) -> dict[str, int]:
        return {started.run.run_id: started.process.wait() for started in self.started}

    def summarize(self, exit_codes: dict[str, int], failed_to_start: int) -> int:
        failed = {run_id: code for run_id, code in exit_codes.items() if code != EXIT_OK}
        for run_id, code in failed.items():
            # Locust exits with --exit-code-on-error (1 by default) when any request failed
            self.logger.error("❌ [%s] Finished With Exit Code %d", run_id, code)

        self.logger.info(
            "🏁 Locust Tests Finished: %d Succeeded, %d Failed, %d Failed To Start",
            len(exit_codes) - len(failed), len(failed), failed_to_start,
        )
        return EXIT_FAILED if failed or failed_to_start else EXIT_OK

    def terminate_all(self) -> None:
        with self.started_lock:
            for started in self.started:
                self.terminate(started)

    def terminate(self, started: StartedRun) -> None:
        try:
            self.logger.warning("Terminating [%s]...", started.run.run_id)
            started.process.terminate()
            started.process.wait(timeout=TERMINATE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            self.logger.warning("Timeout While Terminating [%s], Forcing Kill", started.run.run_id)
            started.process.kill()
        except OSError as error:
            self.logger.warning("OS Error While Terminating [%s]: %s", started.run.run_id, error)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test Runner")
    parser.add_argument(
        "--TEST_PROFILE_PATH",
        type=str,
        default="src/resources/profiles/debug_profile.json",
        help="Path to profile .json"
    )
    parser.add_argument("--DEBUG_ENABLE", type=str_to_bool, default=True, help="Debug Enable")
    return parser.parse_args()


def load_profile(path: str) -> TestsParam:
    with open(path, "r", encoding="utf-8") as f:
        return TestsParam.model_validate(json.load(f))


def apply_percent_profile(profiles: TestsParam) -> None:
    percent = profiles.COMMON_SETTINGS.RUN_SETTINGS.PERCENT_PROFILE
    for element in profiles.elements.values():
        for scenario in element.profile.PROFILE.values():
            for step in scenario.STEPS:
                step.TPS *= percent


def main() -> int:
    args = parse_args()
    profiles = load_profile(args.TEST_PROFILE_PATH)
    apply_percent_profile(profiles)

    date_now = datetime.now().strftime("%Y-%m-%d")
    date_time_now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ProfileLogHelper.process_profiles(
        input_data=profiles,
        base_dir=".",
        date_now=date_now,
        date_time_now=date_time_now,
        debug_enable=args.DEBUG_ENABLE,
        logger=LoggerHelper.setup_logger(date_now=date_now, date_time_now=date_time_now),
    )
    return ParallelLocustRunner(profiles, args.DEBUG_ENABLE, date_now, date_time_now).run()


if __name__ == "__main__":
    sys.exit(main())
