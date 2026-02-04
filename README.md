# Locust Test

![locust_logo.jpg](img/locust_logo.jpg)

Пример тестов на locust

Запуск тестов:

```bash
locust -f src/tests/reqres/t01_create_users/create_users.py
```

```bash
locust -f src/tests/grpc/grpc.py --host=localhost:9090
```

Генерация классов

```bash
poetry run python3 -m grpc_tools.protoc -I./proto --python_out=./pb --grpc_python_out=./pb ./proto/hello.proto
```