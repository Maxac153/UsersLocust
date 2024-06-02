from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import WriteOptions

class Config:
    api_host = 'http://users.bugred.ru'
    pacing_sec = 6

    influx_bucket = 'locust'
    influx_org = 'locust'
    influx_client = InfluxDBClient(
        url='http://tur.local:8086',
        org=influx_org
    )

    influxdb = influx_client.write_api(
        write_options=WriteOptions(
            batch_size=10,
            flush_interval=10_000,
            jitter_interval=2_000,
            retry_interval=5_000
        )
    )


cfg = Config()