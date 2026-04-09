import math

from src.tests.__common.models.profile.profile import Profile


class ProfileHelper:
    @staticmethod
    def get_stap_pace(tps: float, pacing: float) -> float:
        if tps <= 0:
            return pacing

        pace = 1 / tps

        if pace > pacing:
            return pace
        elif 1 - pace / pacing < 0.96:
            return pace * (pacing / pace)

        return pacing

    @staticmethod
    def close_profile(scenario_name: str, debug_enable: str, profile: Profile) -> tuple[float, list[dict[str, int]]]:
        if debug_enable == "true":
            return profile.PROFILE[scenario_name].PACING, [{"duration": 120, "users": 1, "spawn_rate": 1}]
        else:
            profile = profile.PROFILE[scenario_name]
            min_tps = min(step.TPS for step in profile.STEPS)
            pacing = ProfileHelper.get_stap_pace(min_tps, profile.PACING)
            duration = 0
            stages = []
            for step in profile.STEPS:
                duration += 60 * step.HOLD_TIME
                users = math.ceil(step.TPS * pacing)
                stages.append({"duration": duration, "users": users, "spawn_rate": users / step.RAMP_TIME})

            return pacing, stages
