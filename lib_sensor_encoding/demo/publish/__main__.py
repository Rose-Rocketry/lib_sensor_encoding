from ... import TimestampReading, EncodingType, MQTTSensorClient
from time import sleep
import logging
from random import randrange

def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("demo.publish")
    client = MQTTSensorClient()

    cpu_temp_publish = client.create_sensor(
        "cpu_temp",
        {
            "name": "CPU Temperature",
            "readings": [
                TimestampReading,
                {
                    "name": "cpu_temp",
                    "unit": "°C",
                    "encoding": EncodingType.bits_integer_scaled,
                    "bits": 16,
                    "lsb_value": 0.01
                },
            ],
        },
    )

    client.run_background()

    while True:
        sleep(1)
        temp = randrange(2200, 2600) / 100
        logger.info(f"Publishing cpu_temp={temp}")
        cpu_temp_publish(cpu_temp=temp)


if __name__ == "__main__":
    main()
