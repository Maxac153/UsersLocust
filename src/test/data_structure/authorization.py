
class Authorization:

    @staticmethod
    def data_user_json(login: str, password: str) -> dict:
        return {
            "login": f"{login}",
            "password": f"{password}"
        }

