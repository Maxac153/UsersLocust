from typing import Annotated

from pydantic import BaseModel, Field

DurationField = Annotated[int, Field(ge=1, description="Duration in seconds")]
UsersField = Annotated[int, Field(ge=1, description="Target users")]
SpawnRateField = Annotated[float, Field(gt=0, description="Users per second")]


class Stage(BaseModel):
    duration: DurationField
    users: UsersField
    spawn_rate: SpawnRateField
