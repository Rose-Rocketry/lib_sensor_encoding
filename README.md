# Lib Sensor Encoding
A versatile python library for dynamically encoding sensor data to a stable and compact binary format

# Installation
I would recoment installing this library in a [python venv](https://docs.python.org/3/library/venv.html) or simmilar
```sh
pip install git+https://github.com/Rose-Rocketry/lib_sensor_encoding
```

# Example
```python
from lib_sensor_encoding import TimestampReading, EncodingType, SensorEncoder

cpu_temp_encoder = SensorEncoder({
    "name": "CPU Temperature",
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

cpu_temp_data = cpu_temp_encoder.encode(cpu_temp=45.2, open_files=3412, status="chilling")
print(cpu_temp_data.hex())
# > 0005ede1bed5447c4234cccd

print(cpu_temp_encoder.decode(cpu_temp_data))
# > Container: 
#       timestamp = 2022-11-20 01:18:28.625532
#       cpu_temp = 45.20000076293945
```

> For examples that uses all of this library's features, see [\_\_main__.py](./src/lib_sensor_encoding/__main__.py).
> 
> You can run these examples after installing this library with the command `python -m lib_sensor_encoding`
