import logging
import msgpack
import time
from paho.mqtt.client import Client, MQTTMessage
from typing import TypedDict, Literal, Optional, Callable

META_PREFIX = "meta/"
DATA_PREFIX = "data/"

class SensorMetaChannel():
    name: str
    type: Literal["number", "vector", "string", "bool", "timestamp", "object"]
    unit: Optional[str]
    scale: Optional[float]
    components: Optional[tuple[str]]
    minimum: Optional[float]
    maximum: Optional[float]

class SensorMeta(TypedDict):
    name: str
    channels: tuple[SensorMetaChannel]

def apply_scale(meta: SensorMeta, data: tuple, encode: bool) -> tuple:
    def apply_scale_single(channel: SensorMetaChannel, data):
        if "scale" in channel:
            if channel["type"] == "number":
                if encode:
                    return round(data * channel["scale"])
                else:
                    return data / channel["scale"]
            elif channel["type"] == "vector":
                if encode:
                    return tuple(map(lambda d: round(d * channel["scale"]), data))
                else:
                    return tuple(map(lambda d: d / channel["scale"], data))
            else:
                raise ValueError(f"scale only supported for numbers and vectors, not {channel['type']}")
        else:
            return data

    assert len(meta["channels"]) == len(data)
    return tuple(map(apply_scale_single, meta["channels"], data))


class MQTTSensorClient:
    on_sensor_data: Callable[[str, dict], None]
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
    ) -> None:
        self._host = host
        self._port = port
        self._keepalive = keepalive
        self._topic_meta_prefix = topic_prefix + META_PREFIX
        self._topic_data_prefix = topic_prefix + DATA_PREFIX

        self.on_sensor_data = None

        self._subscribed_sensors = set()
        self._discovered_sensors_meta = dict()
        self._created_sensors_meta = dict()
        self._logger = logging.getLogger(MQTTSensorClient.__name__)

        self._client = Client(client_id=client_id, clean_session=True)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.message_callback_add(self._topic_meta_prefix + "#",
                                          self._on_message_meta)
        self._client.message_callback_add(self._topic_data_prefix + "#",
                                          self._on_message_data)
        self._client.enable_logger()

    def subscribe_sensor(self, id: str) -> None:
        """
        Subscribe to a sensor with the given ID.
        """
        if "#" in self._subscribed_sensors:
            return # We're already subscribed to all sensors

        if id in self._subscribed_sensors:
            return

        self._subscribed_sensors.add(id)

        self._subscribe_sensor_meta(id)
        self._subscribe_sensor_data(id)

    def subscribe_all_sensors(self) -> None:
        """
        Subscribe to all sensors
        """
        if "#" in self._subscribed_sensors:
            return # We're already subscribed to all sensors

        self._subscribed_sensors.clear()
        self._subscribed_sensors.add("#")

        self._subscribe_sensor_meta(id)
        self._subscribe_sensor_data(id)

    def create_sensor(self, id: str, meta: SensorMeta):
        self._logger.info(f"Creating sensor {id}")
        self._created_sensors_meta[id] = meta
        if self._client.is_connected():
            self._publish_sensor_meta(id)


    def run_foreground(self):
        self._client.connect(self._host, self._port, self._keepalive)
        self._client.loop_forever()

    def run_background(self):
        self._client.connect_async(self._host, self._port, self._keepalive)
        self._client.loop_start()

    def _publish_sensor_meta(self, id: str):
        return self._client.publish(
            self._topic_meta_prefix + id,
            msgpack.packb(self._created_sensors_meta[id]),
            qos=1,
            retain=True,
        )

    def publish_sensor_data(self, id: str, data: tuple, prepend_timestamp: bool, qos=0, retain=False):
        """
        Publishes a single data point for the given sensor
        **data**: A tuple containing all of the channels of the sensor
        **prepend_timestamp**: If true, the current time is prepended as the first channel
        **qos**: QOS of the MQTT message
        **retain**: Whether to set the retain flag in the MQTT message
        """

        if prepend_timestamp:
            data = (msgpack.Timestamp.from_unix_nano(time.time_ns()),) + data

        if id not in self._created_sensors_meta:
            raise RuntimeError("Sensor must be created before you can publish data")

        data = apply_scale(self._created_sensors_meta[id], data, encode=True)
        data_packed = msgpack.packb(data)

        return self._client.publish(
            self._topic_data_prefix + id,
            data_packed,
            qos=qos,
            retain=False,
        )

    def _subscribe_sensor_meta(self, id: str):
        if self._client.is_connected():
            self._client.subscribe(self._topic_meta_prefix + id, qos=1)

    def _subscribe_sensor_data(self, id: str):
        if self._client.is_connected():
            self._client.subscribe(self._topic_data_prefix + id, qos=0)

    def _on_connect(self, client: Client, userdata, flags, rc):
        self._logger.info(f"Connected with result code {rc}")

        for id in self._subscribed_sensors:
            # Subscribe to messages for subscribed sensors
            # This is needed if sensors are subscribed to while the client is not connected
            # or if the server restarts
            self._subscribe_sensor_meta(id)
            self._subscribe_sensor_data(id)

        for id in self._created_sensors_meta.keys():
            self._publish_sensor_meta(id)

    def _on_disconnect(self, userdata, flags, rc):
        self._logger.warn(f"Disconnected with result code {rc}")


    def _on_message_meta(self, client: Client, userdata, message: MQTTMessage):
        id = message.topic.removeprefix(self._topic_meta_prefix)
        packed = message.payload

        try:
            self._discovered_sensors_meta[id] = msgpack.unpackb(packed, use_list=False)
            self._logger.debug(f"Sensor discovered with id {repr(id)} and {len(self._discovered_sensors_meta[id]['channels'])} channels")
        except Exception as e:
            self._logger.exception("Error decoding metadata:", e)


    def _on_message_data(self, client: Client, userdata, message: MQTTMessage):
        id = message.topic.removeprefix(self._topic_data_prefix)
        if id not in self._discovered_sensors_meta:
            self._logger.warn(f"Received data for unknown sensor {id}, ignoring")
            return

        meta = self._discovered_sensors_meta[id]
        data = msgpack.unpackb(message.payload, use_list=False)
        data = apply_scale(meta, data, encode=False)

        if self.on_sensor_data != None:
            self.on_sensor_data(id, meta, data)
