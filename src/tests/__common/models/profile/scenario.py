from typing import List

from pydantic import BaseModel

from src.tests.__common.models.profile.steps import Step


class Scenario(BaseModel):
    PACING: int
    STEPS: List[Step]
