import pytest
from pydantic import ValidationError

from src.tests.__common.helpers.profile_helper import DEBUG_STAGE, ProfileHelper
from src.tests.__common.models.profile.scenario import Scenario
from src.tests.__common.models.profile.steps import Step


def make_scenario(pacing: float, *steps: tuple[float, float, float]) -> Scenario:
    return Scenario(
        PACING=pacing,
        STEPS=[Step(TPS=tps, RAMP_TIME=ramp, HOLD_TIME=hold) for tps, ramp, hold in steps],
    )


class TestSelectPacing:
    def test_keeps_profile_pacing_when_lowest_step_fits(self):
        assert ProfileHelper.select_pacing(make_scenario(10, (0.5, 1, 1))) == 10

    def test_stretches_pacing_to_one_user_at_lowest_tps(self):
        assert ProfileHelper.select_pacing(make_scenario(5, (0.1, 1, 1), (1, 1, 1))) == pytest.approx(10)


class TestUsersForTps:
    def test_exact_value(self):
        assert ProfileHelper.users_for_tps(0.5, 10) == 5

    def test_float_noise_does_not_add_a_user(self):
        assert ProfileHelper.users_for_tps(0.7, 10) == 7

    def test_rounds_up(self):
        assert ProfileHelper.users_for_tps(0.15, 10) == 2


class TestSpawnRate:
    def test_is_users_per_second_over_ramp_minutes(self):
        assert ProfileHelper.spawn_rate(users_delta=6, ramp_time_minutes=1) == pytest.approx(0.1)

    def test_zero_ramp_switches_at_once(self):
        assert ProfileHelper.spawn_rate(users_delta=6, ramp_time_minutes=0) == 6

    def test_zero_delta_is_still_positive(self):
        assert ProfileHelper.spawn_rate(users_delta=0, ramp_time_minutes=1) == 1


class TestBuildStages:
    def test_durations_include_ramp_and_hold(self):
        scenario = make_scenario(10, (0.5, 1, 3), (1.0, 2, 5))

        stages = ProfileHelper.build_stages(scenario, pacing=10)

        assert [stage.duration for stage in stages] == [4 * 60, (4 + 7) * 60]

    def test_spawn_rate_ramps_only_the_delta(self):
        scenario = make_scenario(10, (0.5, 1, 3), (1.0, 2, 5))

        first, second = ProfileHelper.build_stages(scenario, pacing=10)

        assert (first.users, first.spawn_rate) == (5, pytest.approx(5 / 60))
        assert (second.users, second.spawn_rate) == (10, pytest.approx(5 / 120))

    def test_ramp_down_uses_absolute_delta(self):
        scenario = make_scenario(10, (1.0, 1, 1), (0.5, 1, 1))

        _, second = ProfileHelper.build_stages(scenario, pacing=10)

        assert (second.users, second.spawn_rate) == (5, pytest.approx(5 / 60))

    def test_total_duration_matches_profile_duration(self):
        scenario = make_scenario(10, (0.5, 1, 3), (1.0, 2, 5))

        stages = ProfileHelper.build_stages(scenario, pacing=10)

        assert stages[-1].duration == ProfileHelper.scenario_duration_seconds(scenario)


class TestCloseProfile:
    def test_debug_returns_single_user_stage(self):
        scenario = make_scenario(7, (5, 1, 1))

        plan = ProfileHelper.close_profile(scenario, debug_enable=True)

        assert (plan.pacing, plan.stages) == (7, [DEBUG_STAGE])

    def test_regular_profile(self):
        scenario = make_scenario(10, (0.1, 1, 3), (0.2, 1, 3))

        plan = ProfileHelper.close_profile(scenario, debug_enable=False)

        assert plan.pacing == 10
        assert [stage.users for stage in plan.stages] == [1, 2]


class TestTpsDeviations:
    def test_exact_profile_has_no_deviations(self):
        assert ProfileHelper.tps_deviations(make_scenario(10, (0.5, 1, 1), (1, 1, 1)), pacing=10) == []

    def test_reports_rounding_overshoot(self):
        [deviation] = ProfileHelper.tps_deviations(make_scenario(10, (0.15, 1, 1)), pacing=10)

        assert deviation.step_number == 1
        assert deviation.actual_tps == pytest.approx(0.2)
        assert deviation.percent == pytest.approx(33.33, abs=0.01)


class TestProfileValidation:
    @pytest.mark.parametrize("step", [
        {"TPS": 0, "RAMP_TIME": 1, "HOLD_TIME": 1},
        {"TPS": 1, "RAMP_TIME": -1, "HOLD_TIME": 1},
        {"TPS": 1, "RAMP_TIME": 0, "HOLD_TIME": 0},
    ])
    def test_rejects_invalid_step(self, step):
        with pytest.raises(ValidationError):
            Step.model_validate(step)

    def test_rejects_empty_steps(self):
        with pytest.raises(ValidationError):
            Scenario(PACING=1, STEPS=[])
