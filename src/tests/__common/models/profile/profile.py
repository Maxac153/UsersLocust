from typing import Dict

from pydantic import BaseModel, Field

from src.tests.__common.models.profile.scenario import Scenario


class Profile(BaseModel):
    RUN: Dict[str, str]
    PROFILE: Dict[str, Scenario]
    PROPERTIES: Dict[str, str] = Field(default_factory=dict)
