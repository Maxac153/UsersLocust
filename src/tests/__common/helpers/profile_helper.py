import math
from dataclasses import dataclass

from src.tests.__common.models.profile.scenario import Scenario
from src.tests.__common.models.profile.steps import Step
from src.tests.__common.models.stage.stage import Stage

SECONDS_IN_MINUTE = 60
DEBUG_STAGE = Stage(duration=120, users=1, spawn_rate=1)
# Guards ceil() against float noise: 0.7 * 10 == 7.000000000000001
USERS_PRECISION = 6


@dataclass(frozen=True)
class ClosedModelPlan:
    pacing: float
    stages: list[Stage]


@dataclass(frozen=True)
class TpsDeviation:
    step_number: int
    target_tps: float
    actual_tps: float

    @property
    def percent(self) -> float:
        return (self.actual_tps - self.target_tps) / self.target_tps * 100


class ProfileHelper:
    @staticmethod
    def step_duration_seconds(step: Step) -> float:
        return (step.RAMP_TIME + step.HOLD_TIME) * SECONDS_IN_MINUTE

    @classmethod
    def scenario_duration_seconds(cls, scenario: Scenario) -> float:
        return sum(cls.step_duration_seconds(step) for step in scenario.STEPS)

    @staticmethod
    def select_pacing(scenario: Scenario) -> float:
        # A pacing shorter than 1 / min TPS still needs one user, which overshoots the lowest step
        min_tps = min(step.TPS for step in scenario.STEPS)
        return max(scenario.PACING, 1 / min_tps)

    @staticmethod
    def users_for_tps(tps: float, pacing: float) -> int:
        return math.ceil(round(tps * pacing, USERS_PRECISION))

    @staticmethod
    def spawn_rate(users_delta: int, ramp_time_minutes: float) -> float:
        # Locust rejects spawn_rate == 0; nothing to ramp or no ramp time means switch at once
        ramp_seconds = ramp_time_minutes * SECONDS_IN_MINUTE
        if users_delta == 0 or ramp_seconds == 0:
            return max(users_delta, 1)
        return users_delta / ramp_seconds

    @classmethod
    def build_stages(cls, scenario: Scenario, pacing: float) -> list[Stage]:
        stages = []
        elapsed_seconds = 0.0
        previous_users = 0
        for step in scenario.STEPS:
            users = cls.users_for_tps(step.TPS, pacing)
            elapsed_seconds += cls.step_duration_seconds(step)
            stages.append(
                Stage(
                    duration=round(elapsed_seconds),
                    users=users,
                    spawn_rate=cls.spawn_rate(abs(users - previous_users), step.RAMP_TIME),
                )
            )
            previous_users = users
        return stages

    @classmethod
    def close_profile(cls, scenario: Scenario, debug_enable: bool) -> ClosedModelPlan:
        if debug_enable:
            return ClosedModelPlan(pacing=scenario.PACING, stages=[DEBUG_STAGE])

        pacing = cls.select_pacing(scenario)
        return ClosedModelPlan(pacing=pacing, stages=cls.build_stages(scenario, pacing))

    @classmethod
    def tps_deviations(cls, scenario: Scenario, pacing: float) -> list[TpsDeviation]:
        deviations = []
        for number, step in enumerate(scenario.STEPS, start=1):
            actual_tps = cls.users_for_tps(step.TPS, pacing) / pacing
            if not math.isclose(actual_tps, step.TPS):
                deviations.append(TpsDeviation(number, step.TPS, actual_tps))
        return deviations
