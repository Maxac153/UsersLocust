import importlib.util

from locust.env import Environment

# Параметры нагрузки (меняйте здесь)

test = [
    "get_accounts.py",
    "create_users.py"
]

STAGES = [
    {"duration": 30, "users": 5, "spawn_rate": 2},
    {"duration": 60, "users": 10, "spawn_rate": 2},
    {"duration": 30, "users": 5, "spawn_rate": 1}
]
BETWEEN_MIN, BETWEEN_MAX = 2, 5
HOST = "http://example.com"
RUN_TIME = "3m"

# 1. Динамическая загрузка locustfile.py
spec = importlib.util.spec_from_file_location("locustfile", "locustfile.py")
locust_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(locust_module)

# 2. Рефлексия: патчим параметры
locust_module.StagesShape.stages = STAGES
locust_module.WebsiteUser.wait_time = locust_module.between(BETWEEN_MIN, BETWEEN_MAX)
locust_module.WebsiteUser.host = HOST

# 3. Создаем окружение и запускаем
env = Environment(user_classes=[locust_module.WebsiteUser],
                  load_test_shape=locust_module.StagesShape())
env.create_local_runner()

print(f"Запуск с этапами: {STAGES}")
print(f"wait_time: between({BETWEEN_MIN}, {BETWEEN_MAX})")
print(f"host: {HOST}")

env.runner.start(0, spawn_rate=1)  # Автоматически используется LoadTestShape
env.runner.greenlet.join()  # Ждем завершения

print("Тест завершен")

if __name__ == "__main__":
    pass
