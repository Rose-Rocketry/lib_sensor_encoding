import functools
import logging
from paho.mqtt.client import Client, MQTTMessage
from typing import Optional, Callable
from . import SensorEncoder, SensorMeta

META_PREFIX = "meta/"
DATA_PREFIX = "data/"


class MQTTSensorClient:
    _host: str
    _port: int
    _keepalive: int
    _sensor_discovery_enabled: bool
    _topic_meta_prefix: str
    _topic_data_prefix: str

    _subscribed_sensors: set[str]
    _discovered_sensor_encoders: dict[str, SensorEncoder]
    _created_sensor_encoders: dict[str, SensorEncoder]

    on_sensor_discovered: Optional[Callable[[str, SensorEncoder], None]]
    """
    Called whenever a new sensor is discovered, or an old sensor is updated with new metadata\
    """
    on_sensor_deleted: Optional[Callable[[str], None]]
    """
    Called whenever a sensor is deleted due to it's retained message being deleted, or malformation metadata 
    """
    on_sensor_data: Optional[Callable[[str, dict], None]]
    """
    Called whenever a sensor data is received from a subscribed sensor 
    """

    def __init__(
        self,
        topic_prefix="sensors/",
        host="127.0.0.1",
        port=1883,
        keepalive=60,
        client_id=None,
        sensor_discovery_enabled=False,
    ) -> None:
        self._host = host
        self._port = port
        self._keepalive = keepalive
        self._sensor_discovery_enabled = sensor_discovery_enabled
        self._topic_meta_prefix = topic_prefix + META_PREFIX
        self._topic_data_prefix = topic_prefix + DATA_PREFIX

        self._subscribed_sensors = set()
        self._discovered_sensor_encoders = dict()
        self._created_sensor_encoders = dict()
        self._logger = logging.getLogger(MQTTSensorClient.__name__)

        self.on_sensor_discovered = None
        self.on_sensor_deleted = None
        self.on_sensor_data = None

        self._client = Client(client_id=client_id, clean_session=True)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.message_callback_add(self._topic_meta_prefix + "#",
                                          self._on_message_meta)
        self._client.message_callback_add(self._topic_data_prefix + "#",
                                          self._on_message_data)
        self._client.enable_logger()

    def create_sensor(self, name: str, meta: SensorMeta) -> Callable:
        encoder = SensorEncoder(meta)
        if encoder.length_bytes == None:
            size = "dynamic"
        else:
            size = f"{encoder.length_bytes} byte"

        self._logger.info(f"Creating sensor {repr(name)} with {size} packets")
        self._created_sensor_encoders[name] = encoder
        if self._client.is_connected():
            self._publish_sensor_meta(name)

        return functools.partial(self.publish_sensor_data, name)

    def publish_sensor_data(self, name: str, **kwargs):
        self._publish_sensor_data(name, **kwargs)

    def delete_sensor(self, name: str):
        if name not in self._created_sensor_encoders:
            return

        # Clear the retain message and inform clients of deletion
        self._publish_sensor_meta_delete(name)

        self._logger.info(f"Sensor {repr(name)} deleted")

    def subscribe_sensor(self, name: str) -> None:
        if name in self._subscribed_sensors:
            pass

        self._subscribed_sensors.add(name)

        self._subscribe_sensor_meta(name)
        self._subscribe_sensor_data(name)

    def run_foreground(self):
        self._client.connect(self._host, self._port, self._keepalive)
        self._client.loop_forever()

    def run_background(self):
        self._client.connect_async(self._host, self._port, self._keepalive)
        self._client.loop_start()

    def _publish_sensor_meta(self, name: str):
        return self._client.publish(
            self._topic_meta_prefix + name,
            self._created_sensor_encoders[name].meta_blob,
            qos=1,
            retain=True,
        )

    def _publish_sensor_meta_delete(self, name: str):
        return self._client.publish(
            self._topic_meta_prefix + name,
            b"",
            qos=1,
            retain=True,
        )

    def _publish_sensor_data(self, name: str, **kwargs):
        payload = self._created_sensor_encoders[name].encode(**kwargs)

        return self._client.publish(
            self._topic_data_prefix + name,
            payload,
            qos=0,
        )

    def _subscribe_sensor_meta(self, name: str):
        if not self._sensor_discovery_enabled and self._client.is_connected():
            self._client.subscribe(self._topic_meta_prefix + name, qos=1)

    def _subscribe_sensor_data(self, name: str):
        if self._client.is_connected():
            self._client.subscribe(self._topic_data_prefix + name, qos=0)

    def _on_connect(self, client: Client, userdata, flags, rc):
        self._logger.info(f"Connected with result code {rc}")

        if self._sensor_discovery_enabled:
            # Subscribe to meta messages for all sensors
            client.subscribe(self._topic_meta_prefix + "#", qos=1)

        for name in self._subscribed_sensors:
            # Subscribe to messages for subscribed sensors
            # This is needed if sensors are subscribed to while the client is not connected
            self._subscribe_sensor_meta(name)
            self._subscribe_sensor_data(name)

        for name in self._created_sensor_encoders.keys():
            # Publish metadata for created sensors
            # This is needed if sensors are created to while the client is not connected
            self._publish_sensor_meta(name)

    def _on_disconnect(self, userdata, flags, rc):
        self._logger.warn(f"Disconnected with result code {rc}")

        if self.on_sensor_deleted != None:
            for name in self._discovered_sensor_encoders.keys():
                self.on_sensor_deleted(name)

        self._discovered_sensor_encoders.clear()

    def _on_message_meta(self, client: Client, userdata, message: MQTTMessage):
        name = message.topic.removeprefix(self._topic_meta_prefix)
        blob = message.payload

        existing_encoder = self._discovered_sensor_encoders.get(name)
        if len(blob) == 0:

            if existing_encoder != None:
                self._logger.info(f"Sensor {repr(name)} deleted")
                self._discovered_sensor_encoders.pop(name)

                if self.on_sensor_deleted != None:
                    self.on_sensor_deleted(name)
            else:
                self._logger.info(f"Sensor {repr(name)} deleted (ignored)")

            return
        elif existing_encoder == None:
            self._logger.info(f"New sensor {repr(name)}")
        else:
            # Existing Sensor
            if blob == existing_encoder.meta_blob:
                self._logger.debug(f"Sensor {repr(name)} metadata refreshed")
                return

            self._logger.info(f"New metadata for sensor {repr(name)}")

        try:
            encoder = SensorEncoder(blob)
            self._logger.debug(f"Encoder created for {repr(name)} with {len(encoder.meta_dict['readings'])} readings")
            self._discovered_sensor_encoders[name] = encoder

            if self.on_sensor_discovered != None:
                self.on_sensor_discovered(name, encoder)
        except Exception as e:
            self._logger.exception("Error decoding metadata blob:", e)

            if existing_encoder != None:
                self._discovered_sensor_encoders.pop(name)

                if self.on_sensor_deleted != None:
                    self.on_sensor_deleted(name)

    def _on_message_data(self, client: Client, userdata, message: MQTTMessage):
        name = message.topic.removeprefix(self._topic_data_prefix)
        blob = message.payload

        existing_encoder = self._discovered_sensor_encoders.get(name)

        if existing_encoder == None:
            self._logger.debug(f"Data packet received for unknown sensor {repr(name)}")
            return

        try:
            data = existing_encoder.decode(blob)
            self._logger.debug(f"Data packet received for sensor {repr(name)}")

            if self.on_sensor_data != None:
                self.on_sensor_data(name, data)
        except Exception as e:
            self._logger.exception(f"Malformed data packet received for sensor {repr(name)}", e)
