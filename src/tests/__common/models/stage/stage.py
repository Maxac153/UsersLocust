from typing import Annotated

from pydantic import BaseModel, Field


class Stage(BaseModel):
    duration: Annotated[int, Field(ge=1, description="Duration in seconds")]
    users: Annotated[int, Field(ge=1, description="Target users")]
    spawn_rate: Annotated[float, Field(gt=0, description="Users per second")]
