import json
import os
from datetime import datetime
from datetime import timedelta
from logging import Logger
from pathlib import Path
from typing import Any, Dict, List

from src.tests.__common.models.profile.scenario import Scenario
from src.tests.__common.models.profile.tests_param import TestsParam


class ProfileLogHelper:
    LINE_SEPARATOR = (
        "+---------------------------------------------------------------------------------------------------------+"
    )

    @staticmethod
    def format_duration(time_sec: float) -> str:
        seconds = int(time_sec)
        days = seconds // 86400
        remainder = seconds % 86400
        hours = remainder // 3600
        remainder %= 3600
        min_ = remainder // 60
        sec = remainder % 60
        return (
            f"{str(days).zfill(2)} d. {str(hours).zfill(2)} h. "
            f"{str(min_).zfill(2)} m. {str(sec).zfill(2)} s."
        )

    @staticmethod
    def pad2(n: int) -> str:
        return str(n).zfill(2)

    @classmethod
    def format_datetime(cls, dt: datetime) -> str:
        return (
            f"{cls.pad2(dt.hour)}:{cls.pad2(dt.minute)}:{cls.pad2(dt.second)} "
            f"{cls.pad2(dt.day)}-{cls.pad2(dt.month)}-{dt.year}"
        )

    @staticmethod
    def calculate_profile_duration(scenario: Scenario) -> float:
        if not scenario.STEPS:
            return 0
        total = 0
        for step in scenario.STEPS:
            ramp_time = float(getattr(step, "RAMP_TIME", 0))
            hold_time = float(getattr(step, "HOLD_TIME", 0))
            total += (ramp_time + hold_time) * 60
        return total

    @staticmethod
    def create_logs_dir(base_dir: str, profile_name: str, date_now: str, date_time_now: str) -> str:
        logs_dir = os.path.join(base_dir, "output", "logs", date_now, date_time_now, profile_name)
        os.makedirs(logs_dir, exist_ok=True)
        return logs_dir

    @classmethod
    def build_profile_info(
            cls,
            scenario: Scenario,
            start_date: datetime,
            end_date: datetime,
    ) -> Dict[str, Any]:
        step_logs: List[str] = []
        step_intervals: Dict[str, str] = {}
        step_start = start_date

        pacing = scenario.PACING

        for i, step in enumerate(scenario.STEPS):
            ramp_time = float(getattr(step, "RAMP_TIME", 0))
            hold_time = float(getattr(step, "HOLD_TIME", 0))

            step_start += timedelta(minutes=ramp_time)
            step_end = step_start + timedelta(minutes=hold_time)

            start_ms = int(step_start.timestamp() * 1000)
            end_ms = int(step_end.timestamp() * 1000)

            step_key = f"step_{i + 1}"
            step_intervals[step_key] = f"from={start_ms}&to={end_ms}"

            step_num = str(i + 1).zfill(2)
            step_logs.append(
                f"Step #{step_num}            from={start_ms}&to={end_ms} (TPS: {step.TPS})"
            )

            step_start = step_end

        first_step = scenario.STEPS[0] if scenario.STEPS else None
        first_ramp_minutes = float(getattr(first_step, "RAMP_TIME", 0)) if first_step else 0
        ramp_up_end_time = start_date + timedelta(minutes=first_ramp_minutes)

        start_ms = int(start_date.timestamp() * 1000)
        end_ms = int(end_date.timestamp() * 1000)
        ramp_up_ms = int(ramp_up_end_time.timestamp() * 1000)
        total_duration_s = (end_date - start_date).total_seconds()

        return {
            "startTime": cls.format_datetime(start_date),
            "endTime": cls.format_datetime(end_date),
            "totalDuration": cls.format_duration(total_duration_s),
            "grafanaFull": f"from={start_ms}&to={end_ms}",
            "grafanaRampUp": f"from={ramp_up_ms}&to={end_ms}",
            "pacing": pacing,
            "steps": step_logs,
            "stepIntervals": step_intervals,
        }

    @classmethod
    def log_profile_info(
            cls,
            scenario_name: str,
            profile_info: Dict[str, Any],
            logs_dir: str,
            log_file_name: str,
            logger: Logger,
            is_longest: bool = False,
    ) -> Dict[str, Any]:
        log_lines = []

        if is_longest:
            log_lines.append(cls.LINE_SEPARATOR)
            log_lines.append("|                                             Longest Scenario")

        log_lines.append(cls.LINE_SEPARATOR)
        log_lines.append(f"|  Scenario Name:      {scenario_name.ljust(80)[:80]}")
        log_lines.append(cls.LINE_SEPARATOR)
        log_lines.append(f"|  Start Time:         {profile_info['startTime'].ljust(80)[:80]}")
        log_lines.append(cls.LINE_SEPARATOR)
        log_lines.append(f"|  Scenario End Time:  {profile_info['endTime'].ljust(80)[:80]}")
        log_lines.append(cls.LINE_SEPARATOR)
        log_lines.append(f"|  Total Duration:     {profile_info['totalDuration'].ljust(80)[:80]}")
        log_lines.append(cls.LINE_SEPARATOR)
        log_lines.append(f"|  Grafana (Full):     {profile_info['grafanaFull'].ljust(80)[:80]}")
        log_lines.append(cls.LINE_SEPARATOR)
        log_lines.append(f"|  Grafana (RampUp):   {profile_info['grafanaRampUp'].ljust(80)[:80]}")
        log_lines.append(cls.LINE_SEPARATOR)
        log_lines.append(f"|  Pacing:             {str(profile_info['pacing']).ljust(80)[:80]}")
        log_lines.append(cls.LINE_SEPARATOR)

        for step in profile_info["steps"]:
            log_lines.append(f"|  {step.ljust(78)[:78]}")

        log_lines.append(cls.LINE_SEPARATOR)

        for line in log_lines:
            logger.info(line)

        log_path = os.path.join(logs_dir, f"{log_file_name}.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n".join(log_lines) + "\n")

        return profile_info

    @classmethod
    def save_profile_json(
            cls,
            profile_info: Dict[str, Any],
            logs_dir: str,
            log_file_name: str,
    ) -> None:
        json_path = Path(logs_dir) / f"{log_file_name}.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)

        json_data = {
            "grafana_full": profile_info["grafanaFull"],
            "grafana_without_ramp_up": profile_info["grafanaRampUp"],
            "steps": profile_info["stepIntervals"],
        }

        json_path.write_text(
            json.dumps(json_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def get_scenario_entries(input_data: TestsParam) -> List[Dict[str, Any]]:
        elements = input_data.elements
        scenarios: List[Dict[str, Any]] = []

        for element_name, element in elements.items():
            profile_root = element.profile.PROFILE
            for scenario_name, scenario in profile_root.items():
                if scenario.STEPS:
                    scenarios.append(
                        {
                            "elementName": element_name,
                            "scenarioName": scenario_name,
                            "scenario": scenario,
                        }
                    )
        return scenarios

    @classmethod
    def process_profiles(
            cls,
            input_data: TestsParam,
            base_dir: str = ".",
            date_now: str = datetime.now().strftime("%Y-%m-%d"),
            date_time_now: str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
            logger: Logger = None,
            debug_enable: str = "true",
    ) -> None:
        run_settings = input_data.COMMON_SETTINGS.RUN_SETTINGS
        if debug_enable == "true":
            logger.info("DEBUG_ENABLE = true: Skipping Profile Logging")
            return

        profile_name = run_settings.PROFILE_NAME
        logs_dir = cls.create_logs_dir(base_dir, profile_name, date_now, date_time_now)

        scenarios = cls.get_scenario_entries(input_data)
        logger.info(f"📊 Found {len(scenarios)} Scenarios Across All Elements")

        if not scenarios:
            logger.info("No Scenarios Found, Skipping Profile Processing")
            return

        longest_scenario = None
        longest_duration = 0.0

        for scenario in scenarios:
            duration = cls.calculate_profile_duration(scenario["scenario"])
            logger.info(f"   {scenario['elementName']}/{scenario['scenarioName']}: {duration}s")
            if duration > longest_duration:
                longest_duration = duration
                longest_scenario = scenario

        if longest_scenario:
            logger.info(
                f"🏆 Longest: {longest_scenario['elementName']}/{longest_scenario['scenarioName']} ({longest_duration}s)"
            )

            start_date = datetime.now()
            end_date = start_date + timedelta(seconds=longest_duration)

            profile_info = cls.build_profile_info(
                longest_scenario["scenario"],
                start_date,
                end_date,
            )

            cls.log_profile_info(
                longest_scenario["scenarioName"],
                profile_info,
                logs_dir,
                f"{profile_name}_longest_scenario",
                logger,
                is_longest=True,
            )
            cls.save_profile_json(
                profile_info,
                logs_dir,
                f"{profile_name}_longest_scenario",
            )

        for scenario in scenarios:
            if longest_scenario and scenario["scenarioName"] == longest_scenario["scenarioName"]:
                continue

            start_date = datetime.now()
            duration = cls.calculate_profile_duration(scenario["scenario"])
            end_date = start_date + timedelta(seconds=duration)
            profile_info = cls.build_profile_info(
                scenario["scenario"],
                start_date,
                end_date,
            )
            cls.log_profile_info(
                scenario["scenarioName"],
                profile_info,
                logs_dir,
                f"{profile_name}_scenarios",
                logger,
                is_longest=False,
            )
