from typing import Annotated, List

from pydantic import BaseModel, Field

from src.tests.__common.models.profile.steps import Step


class Scenario(BaseModel):
    PACING: Annotated[float, Field(gt=0, description="Iteration pacing, seconds")]
    STEPS: Annotated[List[Step], Field(min_length=1)]
