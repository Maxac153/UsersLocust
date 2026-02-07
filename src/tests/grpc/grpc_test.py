import time
from locust import User, task, between
import grpc
import grpc.experimental.gevent as gevent_grpc

from proto import hello_pb2_grpc, hello_pb2

gevent_grpc.init_gevent()


from locust import events


class GrpcUser(User):
    wait_time = between(1, 3)

    def on_start(self):
        self.channel = grpc.insecure_channel("localhost:9090", [('grpc.keepalive_time_ms', '10000')])
        self.stub = hello_pb2_grpc.HelloServiceStub(self.channel)

    @task
    def say_hello(self):
        start_time = time.time()
        try:
            request = hello_pb2.HelloRequest(name="мир")
            response = self.stub.sayHello(request, timeout=5)

            events.request.fire(
                request_type="grpc",
                name="sayHello",
                response_time=(time.time() - start_time) * 1000,
                response_length=len(str(response.message)),
                exception=None
            )

            print(f"✅ massage: {response.message} age: {response.age}")

        except Exception as e:
            events.request.fire(
                request_type="grpc",
                name="sayHello",
                response_time=(time.time() - start_time) * 1000,
                response_length=0, exception=e
            )
            print(f"❌ {e}")

    def on_stop(self):
        self.channel.close()
