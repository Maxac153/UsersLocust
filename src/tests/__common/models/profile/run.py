from typing import List

from pydantic import BaseModel


class Run(BaseModel):
    ENV: List[str]
    LOAD_GENERATOR: str
    TEST_PATH: str
