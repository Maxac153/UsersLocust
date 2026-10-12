from pydantic import BaseModel

from src.tests.__common.models.profile.profile import Profile


class Element(BaseModel):
    X: int
    Y: int
    PROFILE: Profile
