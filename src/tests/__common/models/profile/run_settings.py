from pydantic import BaseModel


class RunSettings(BaseModel):
    PROFILE_NAME: str
    SYSTEM_NAME: str
    LEVEL_CONSOLE_LOG: str
    LEVEL_FILE_LOG: str
    DATASOURCE_HOST: str
    DATASOURCE_PORT: int
    PERCENT_PROFILE: int
