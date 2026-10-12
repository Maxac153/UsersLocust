import json
from typing import Any


class PropertyHelper:
    @staticmethod
    def read_properties(test_properties: str | None = None, *properties_paths: str) -> dict[str, Any]:
        properties = {}

        # Параметры из файлов
        for path in properties_paths:
            with open(path, 'r', encoding='utf-8') as f:
                properties.update(json.load(f))

        # Параметры теста из системы
        if test_properties:
            properties.update(json.loads(test_properties))

        # Параметры из .env (redis_login, redis_password, db_login, db_password, ...)
        for path in PropertyHelper.env_paths(properties.get("ENV")):
            with open(path, 'r', encoding='utf-8') as f:
                properties.update(json.load(f))

        return properties

    @staticmethod
    def env_paths(env: list[str] | str | None) -> list[str]:
        # Profiles pass a list (RUN.ENV); a comma-separated string is still accepted for direct `locust --PROPERTIES` runs
        if not env:
            return []
        if isinstance(env, str):
            return [path.strip() for path in env.split(",")]
        return list(env)
