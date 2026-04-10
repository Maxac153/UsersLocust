from typing import Dict

from pydantic import BaseModel

from src.tests.__common.models.profile.run import Run
from src.tests.__common.models.profile.scenario import Scenario


class Profile(BaseModel):
    RUN: Run
    PROFILE: Dict[str, Scenario]
    PROPERTIES: Dict[str, str]
