import json


class PropertyHelper:
    @staticmethod
    def read_properties(test_properties: str = None, *properties_paths: str) -> dict[str, str]:
        properties = {}

        # Параметры из файлов
        for path in properties_paths:
            with open(path, 'r', encoding='utf-8') as f:
                properties.update(json.load(f))

        # Параметры теста из системы
        if test_properties:
            properties.update(json.loads(test_properties))

        # Параметры из .env (redis_login, redis_password, db_login, db_password, ...)
        env = properties.get("ENV")
        if env:
            for path in env:
                with open(path, 'r', encoding='utf-8') as f:
                    properties.update(json.load(f))

        return properties
