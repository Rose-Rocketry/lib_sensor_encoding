# Lib Sensor Encoding
A python library for efficiently encoding and decoding sensor data over MQTT

## Installation
I would recommend installing this library in a [python venv](https://docs.python.org/3/library/venv.html) or similar
```bash
pip install git+https://github.com/Rose-Rocketry/lib_sensor_encoding
```

## Encoding Example
```python
from lib_sensor_encoding import TimestampReading, EncodingType, SensorEncoder

cpu_encoder = SensorEncoder({
    "name": "CPU Info",
    "readings": [
        TimestampReading,
        {
            "name": "cpu_temp",
            "unit": "°C",
            "encoding": EncodingType.float,
            "bits": 32,
        },
    ],
})
print(cpu_encoder.meta_blob.hex())
# > 0143505520496e666f00021e74696d65...

cpu_data = cpu_encoder.encode(cpu_temp=45.2)
print(cpu_data.hex())
# > 0005ede1bed5447c4234cccd

print(cpu_encoder.decode(cpu_data))
# > Container: 
#       timestamp = 2022-11-20 01:18:28.625532
#       cpu_temp = 45.20000076293945
```

## Publish Example
```python
from lib_sensor_encoding import TimestampReading, EncodingType, MQTTSensorClient
from time import sleep

client = MQTTSensorClient()
client.run_background()
cpu_publish = client.create_sensor(
    "cpu",
    {
        "name": "CPU Info",
        "readings": [
            TimestampReading,
            {
                "name": "cpu_temp",
                "unit": "°C",
                "encoding": EncodingType.float,
                "bits": 32,
            },
        ],
    },
) # Publishes a binary metadata packet to the broker

sleep(1) # Give the subscriber time to subscribe
cpu_publish(cpu_temp=45.2) # Publishes a binary data packet to the broker
```

## Subscribe Example
```python
from ... import SensorEncoder, MQTTSensorClient
def sensor_data(name: str, data: dict):
    print(data)

client = MQTTSensorClient(sensor_discovery_enabled=True)
client.on_sensor_data = sensor_data
client.subscribe_sensor("cpu")
client.run_foreground()
# > Container: 
#       timestamp = 2022-11-20 01:18:28.625532
#       cpu_temp = 45.20000076293945
```


## More Examples

For more complete examples that uses almost all of this library's features, see the [demos](./lib_sensor_encoding/demo).

You can run the system status and MPU6050 encoding example with `python -m lib_sensor_encoding.demo.encoding`

To run the publish and subscribe examples, first you need an MQTT broker running on localhost.
This is most easily achieved by installing mosquitto and running `mosquitto` in a terminal.
Start the publisher and subscriber in separate terminals with `python -m lib_sensor_encoding.demo.publish` and `python -m lib_sensor_encoding.demo.subscribe`
> This library is designed to be fault-tolerant. In the previous example if any component (broker, publisher, or subscriber) is restarted, all other components continue to work without issue.

