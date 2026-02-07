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

```bash
locust -f test.py --host=https://example.com
```

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: [ 'localhost:9090' ]

  - job_name: 'locust'
    static_configs:
      - targets: [ '192.168.31.252:9646' ]

  - job_name: 'spring-boot-app'
    metrics_path: '/actuator/prometheus'
    static_configs:
      - targets: [ '192.168.31.252:8080' ]
```
