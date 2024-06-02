from faker import Faker


class Registration:

    @staticmethod
    def random_reg_user():
        faker = Faker()
        return {
            "email": f"{faker.email()}",
            "name": f"max_{faker.name()}",
            "password": f"{faker.password(length=16, special_chars=True, digits=True, upper_case=True, lower_case=True)}"
        }
