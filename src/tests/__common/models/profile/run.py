from pydantic import BaseModel


class Run(BaseModel):
    ENV: str
    LOAD_GENERATOR: str
    TEST_PATH: str
