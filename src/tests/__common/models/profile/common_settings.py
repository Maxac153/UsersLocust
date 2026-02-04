from typing import Dict

from pydantic import BaseModel, Field

from src.tests.__common.models.profile.run_settings import RunSettings


class CommonSettings(BaseModel):
    RUN_SETTINGS: RunSettings
    PROPERTIES: Dict[str, str] = Field(default_factory=dict)
