import time

from httpx import Request, Response, HTTPStatusError, HTTPError
from locust.env import Environment


def locust_request_event_hook(request: Request) -> None:
    """
    Хук, вызываемый HTTPX перед отправкой запроса.

    Сохраняет текущее время (timestamp) в поле request.extensions["start_time"],
    чтобы затем можно было вычислить длительность запроса.
    """
    request.extensions["start_time"] = time.time()


def locust_response_event_hook(environment: Environment):
    """
    Возвращает функцию-хук для HTTPX, вызываемую после получения ответа.

    Этот хук:
    - извлекает информацию о запросе (метод, URL, маршрут),
    - считает длительность ответа,
    - определяет длину тела,
    - фиксирует исключения (если они возникли),
    - и отправляет всё это как событие в Locust.

    Параметры:
    ----------
    environment : locust.env.Environment
        Объект окружения Locust, содержащий систему событий (events),
        через которую отправляются данные для HTML-отчёта.

    Возвращает:
    -----------
    Callable[[Response], None]
        Замкнутая функция, вызываемая после каждого ответа HTTPX.
    """

    # Вложенная функция (замыкание), которая будет реально использоваться как хук.
    # Она "запоминает" переменную `environment` из внешней области видимости.
    def inner(response: Response) -> None:
        exception: HTTPError | HTTPStatusError | None = None

        # Пытаемся проверить статус ответа. Если он не 2xx/3xx — сохраняем исключение.
        try:
            response.raise_for_status()
        except (HTTPError, HTTPStatusError) as error:
            exception = error

        # Извлекаем оригинальный запрос, чтобы получить информацию о маршруте.
        request = response.request

        # Получаем route из extensions (если был передан явно),
        # иначе используем "сырое" значение path из URL.
        request_name = request.extensions.get("request_name", request.url.path)

        # Вытаскиваем метку времени начала запроса.
        # Если её не было (что маловероятно) — подставляем текущую.
        start_time = request.extensions.get("start_time", time.time())

        # Вычисляем время ответа в миллисекундах.
        response_time = (time.time() - start_time) * 1000

        # Считаем длину тела ответа в байтах.
        response_length = len(response.read())

        # Отправляем событие в систему метрик Locust.
        # Это позволяет отобразить запрос в HTML-отчёте.
        environment.events.request.fire(
            request_type="HTTP",  # Тип запроса (можно указать любое значение, например "gRPC")
            name=request_name,  # Имя маршрута — с методом, агрегируется в отчёте
            response_time=response_time,  # Длительность запроса
            response_length=response_length,  # Длина тела
            response=response,  # Сам объект ответа (можно использовать в кастомных хендлерах)
            exception=exception,  # Ошибка, если была
            context=None  # Можно передавать контекст — например, пользователь или сессионные данные
        )

    return inner  # Возвращаем замыкание
