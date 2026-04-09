import argparse
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List

from src.tests.__common.helpers.profile_helper import ProfileHelper
from src.tests.__common.helpers.profile_log_helper import ProfileLogHelper
from src.tests.__common.helpers.setup_logger_helpers import setup_logger
from src.tests.__common.models.profile.tests_param import TestsParam


class ParallelLocustRunner:
    def __init__(
            self,
            profiles: TestsParam,
            debug_enable: str,
            data_time_now: str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ) -> None:
        self.data_time_now = data_time_now
        self.logger = setup_logger(date_time=self.data_time_now)
        self.processes_lock = threading.Lock()
        self.processes = []
        self.profiles = profiles
        self.debug_enable = debug_enable

    def create_commands(self) -> List[List[str]]:
        """Generates Commands For All Tests"""
        commands = []
        for test_name in self.profiles.elements:
            test = self.profiles.elements[test_name]
            for scenario_name in test.profile.PROFILE:
                pacing, stages = ProfileHelper.close_profile(scenario_name, self.debug_enable, test.profile)
                cmd = [
                    "locust", "-f", test.profile.RUN.TEST_PATH,
                    f"--DEBUG_ENABLE={self.debug_enable}",
                    f"--PACING={pacing}",
                    f"--STAGES={json.dumps(stages)}",
                    f"--PROPERTIES={json.dumps(test.profile.PROPERTIES)}",
                    "--host=localhost",
                    "--headless",
                    "--logfile", f"output/logs/{self.data_time_now}/{test_name}.log"
                ]
                commands.append(cmd)

        return commands

    def log_reader(self, process: subprocess.Popen, prefix: str) -> None:
        """Reads Process Logs In Real-Time With Prefix"""
        try:
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.logger.debug("[%s] %s", prefix, line.rstrip())
        except (OSError, ValueError) as e:
            self.logger.exception("Failed To Read Logs From %s: %s", prefix, e)
        except Exception as e:
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            self.logger.exception("Unexpected Error While Reading Logs From %s: %s", prefix, e)

    def run_single_test(self, cmd: List[str], index: int) -> None:
        """Runs One Test"""
        prefix = f"LOCUST-{index + 1:02d}"
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                # Низкий приоритет на Linux
                preexec_fn=lambda: os.nice(10) if os.name == 'posix' else None
            )

            self.logger.info("🚀 [%s] Started (PID: %s)", prefix, process.pid)

            log_thread = threading.Thread(
                target=self.log_reader,
                args=(process, prefix),
                daemon=True
            )
            log_thread.start()

            with self.processes_lock:
                self.processes.append((process, prefix))

        except Exception as e:
            self.logger.error("Failed To Start %s: %s", prefix, e)

    def run_parallel_unlimited(self, max_workers: int = 100) -> None:
        """Runs ALL Tests In Parallel"""
        commands = self.create_commands()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self.run_single_test, cmd, i)
                for i, cmd in enumerate(commands)
            ]
            for future in futures:
                future.result()

        self.logger.info("✅ Started %s Locust Tests In Parallel", len(commands))

    def monitor_status(self):
        """Status Monitoring"""
        while any(p[0].poll() is None for p in self.processes):
            with self.processes_lock:
                running = sum(1 for p, _ in self.processes if p.poll() is None)
                finished = len(self.processes) - running

            self.logger.info("⏱️ Running: %d | Finished: %d | Total: %d", running, finished, len(self.processes))
            time.sleep(10)

    def run(self):
        """Main Runner"""
        try:
            self.run_parallel_unlimited()
            monitor_thread = threading.Thread(
                target=self.monitor_status,
                name="  Monitor ",
                daemon=True
            )
            monitor_thread.start()

            # Ждём завершения всех процессов
            for process, prefix in self.processes:
                process.wait()

            self.logger.info("🎉 All %d Locust Tests Completed", len(self.processes))

        except KeyboardInterrupt:
            self.logger.warning("🛑 Ctrl+C - Terminating All Processes...")
            with self.processes_lock:
                for process, prefix in self.processes:
                    try:
                        self.logger.warning("Terminating %s...", prefix)
                        process.terminate()
                        process.wait(timeout=10)
                    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
                        self.logger.warning("Timeout Or Error While Terminating %s, Forcing Kill: %s", prefix, e)
                        process.kill()
                    except OSError as e:
                        self.logger.warning("OS Error While Terminating %s: %s", prefix, e)
            sys.exit(0)


# Пример использования
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Runner")
    parser.add_argument(
        "--TEST_PROFILE_PATH",
        type=str,
        default="src/resources/profiles/debug_profile.json",
        help="Path to profile .json"
    )
    parser.add_argument(
        "--DEBUG_ENABLE",
        type=str,
        default="true",
        help="Debug Enable"
    )
    args = parser.parse_args()

    with open(args.TEST_PROFILE_PATH, "r", encoding="utf-8") as f:
        profile_json = json.load(f)
    json_object = TestsParam.model_validate(profile_json)
    date_time_now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ProfileLogHelper.process_profiles(
        input_data=json_object,
        base_dir=".",
        date_time_now=date_time_now,
        debug_enable=args.DEBUG_ENABLE,
        logger=setup_logger(date_time=date_time_now),
    )
    runner = ParallelLocustRunner(json_object, args.DEBUG_ENABLE, date_time_now)
    runner.run()
