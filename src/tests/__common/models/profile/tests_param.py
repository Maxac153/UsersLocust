from typing import Dict, List

from pydantic import BaseModel

from src.tests.__common.models.profile.common_settings import CommonSettings
from src.tests.__common.models.profile.connection import Connection
from src.tests.__common.models.profile.element import Element
from src.tests.__common.models.profile.form import Form


class TestsParam(BaseModel):
    elements: Dict[str, Element]
    connections: List[Connection]
    form: Form
    COMMON_SETTINGS: CommonSettings
