from typing import List

from pydantic import RootModel

from src.tests.__common.models.stage.stage import Stage


class StagesConfig(RootModel):
    root: List[Stage]
