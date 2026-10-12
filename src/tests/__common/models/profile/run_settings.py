from typing import Annotated

from pydantic import BaseModel, Field


class RunSettings(BaseModel):
    DATASOURCE_URL: str
    INFLUX_BUCKET: str
    INFLUX_ORG: str
    PROMETHEUS_PORT: str
    PROFILE_NAME: str
    SYSTEM_NAME: str
    # Scales every step TPS after validation, so 0 would bypass the TPS > 0 check
    PERCENT_PROFILE: Annotated[float, Field(gt=0)]
    LOG_LEVEL: str
