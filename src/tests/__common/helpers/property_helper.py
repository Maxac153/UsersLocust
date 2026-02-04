import json


class PropertyHelper:
    @staticmethod
    def read_properties(test_settings: dict[str, str] = None, *properties_paths) -> dict[str, str]:
        properties = {}

        # Параметры из файлов
        for path in properties_paths:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                properties.update(data)

        # Параметры теста из системы
        if test_settings:
            properties.update(test_settings)

        # Параметры из .env (redis_login, redis_password, db_login, db_password, ...)
        env = properties.get("ENV")
        if env:
            for path in env.split(","):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    properties.update(data)

        return properties
