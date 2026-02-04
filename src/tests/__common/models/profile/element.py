from pydantic import BaseModel

from src.tests.__common.models.profile.profile import Profile


class Element(BaseModel):
    x: int
    y: int
    profile: Profile
