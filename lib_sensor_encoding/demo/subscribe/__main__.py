from ... import SensorEncoder, MQTTSensorClient
import logging

def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("demo.receive")

    def sensor_discovered(name: str, encoder: SensorEncoder):
        print("meta:", encoder.meta_dict)
        logger.info(f"Subscribing to {repr(name)}")

        client.subscribe_sensor(name)

    def sensor_data(name: str, data: dict):
        logger.info(f"Data for {repr(name)} {data}")

    client = MQTTSensorClient(sensor_discovery_enabled=True)
    client.on_sensor_discovered = sensor_discovered
    client.on_sensor_data = sensor_data
    client.run_foreground()


if __name__ == "__main__":
    main()
