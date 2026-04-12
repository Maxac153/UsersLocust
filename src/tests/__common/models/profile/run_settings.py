from pydantic import BaseModel


class RunSettings(BaseModel):
    DATASOURCE_URL: str
    INFLUX_BUCKET: str
    INFLUX_ORG: str
    PROMETHEUS_PORT: str
    PROFILE_NAME: str
    SYSTEM_NAME: str
    PERCENT_PROFILE: float
    LOG_LEVEL: str
