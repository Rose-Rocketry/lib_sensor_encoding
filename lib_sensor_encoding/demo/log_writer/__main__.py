import construct
import logging
from typing import BinaryIO
from pathlib import Path
from ... import MQTTSensorClient, SensorEncoder
"""
Format overview:
Each sensor metadata configuration gets it's own log file. It has a series of packets, each prefixed by a 16-bit size field.
The first packet is the metadata packet, and the rest are data packets.
"""

_log_entry = construct.Prefixed(construct.Int16ub, construct.GreedyBytes)


def get_with_suffix(path: Path) -> Path:
    """
    Gets a non-existent path, adding a numbered suffix if needed
    """

    def generate_path(suffix: int):
        return path.parent / (path.name + "-" + str(suffix))

    suffix = 0
    new_path = generate_path(suffix)

    while new_path.exists():
        suffix += 1
        new_path = generate_path(suffix)

    return new_path


LOG_DIR = get_with_suffix(Path("logs"))


class LogSensorWriter:

    def __init__(self, name: str, blob: bytes) -> None:
        self._logger = logging.getLogger("demo.log_writer")
        self._path = get_with_suffix(LOG_DIR / (name.encode().hex()))
        self._path.parent.mkdir(parents=True, exist_ok=True)

        self._logger.info(f"Opening {self._path}")
        self._writer = open(self._path, "wb", buffering=0)

        self.blob = blob
        self.write_packet(blob)

    def write_packet(self, packet: bytes):
        self._writer.write(_log_entry.build(packet))

    def close(self):
        self._logger.info(f"Closing {self._path}")
        self._writer.close()


class LogWriter:
    _writers: dict[str, LogSensorWriter]

    def __init__(self, client: MQTTSensorClient) -> None:
        self._logger = logging.getLogger("demo.log_writer")
        self._client = client
        self._client._on_message_callback_is_raw = True
        self._client.on_sensor_discovered = self.on_sensor_discovered
        self._client.on_sensor_deleted = self.on_sensor_deleted
        self._client.on_sensor_data_raw = self.on_sensor_data_raw
        self._writers = dict()

    def on_sensor_discovered(self, name: str, encoder: SensorEncoder) -> None:
        writer = self._writers.get(name)

        if writer != None:
            if writer.blob == encoder.meta_blob:
                return
            else:
                self._writers.pop(name).close()

        writer = LogSensorWriter(name, encoder.meta_blob)

        self._writers[name] = writer

    def on_sensor_deleted(self, name: str) -> None:
        writer = self._writers.get(name)

        if writer != None:
            self._writers.pop(name)
            writer.close()

    def on_sensor_data_raw(self, name: str, packet: bytes) -> None:
        writer = self._writers.get(name)
        if writer != None:
            writer.write_packet(packet)

    def close(self):
        for writer in self._writers.values():
            writer.close()

        self._writers.clear()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    client = MQTTSensorClient(sensor_discovery_enabled=True,
                              sensor_discovery_subscribe_all=True)
    writer = LogWriter(client)
    client.run_foreground()
