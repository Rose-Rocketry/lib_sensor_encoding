from .. import MQTTSensorClient
import logging
import time
from random import random

SENSOR_ID = "rand"


def main():
    logging.basicConfig(level=logging.INFO)

    client = MQTTSensorClient()
    client.create_sensor(
        SENSOR_ID,
        {
            "name": "Random Testing Sensor",
            "channels": (
                {"name": "timestamp", "type": "timestamp"},
                {
                    "name": "Random Percent",
                    "type": "number",
                    "unit": "%",
                },
                {
                    "name": "Random Percent (scaled)",
                    "type": "number",
                    "scale": 10,
                    "unit": "%",
                },
                {
                    "name": "Random Vector",
                    "type": "vector",
                    "unit": "m/s²",
                    "scale": 10,
                    "components": ("x", "y", "z"),
                },
                {"name": "Status", "type": "string"},
            ),
        },
    )

    client.run_background()

    while True:
        time.sleep(1)
        client.publish_sensor_data(
            SENSOR_ID,
            (
                random() * 100,
                random() * 100,
                (
                    random() * 20 - 10,
                    random() * 20 - 10,
                    random() * 20 - 10,
                ),
                "vibing"
            ),
            prepend_timestamp=True,
        )


if __name__ == "__main__":
    main()
