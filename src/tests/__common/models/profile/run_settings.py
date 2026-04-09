from pydantic import BaseModel


class RunSettings(BaseModel):
    DATASOURCE_URL: str
    METRICS_BACKEND: str
    PROFILE_NAME: str
    SYSTEM_NAME: str
    PERCENT_PROFILE: float
    LOG_LEVEL: str
