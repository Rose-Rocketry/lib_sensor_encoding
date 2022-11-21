import construct
from datetime import datetime
from typing import Union
from .sensor_meta import _sensor_meta_struct, SensorMeta, SensorMetaReading, EncodingType, _null_terminated_string


class _SensorReadingScalingAdaptor(construct.Adapter):

    def __init__(self, reading: SensorMetaReading, subcon) -> None:
        super().__init__(subcon)

        self.lsb_value = reading["lsb_value"]
        self.zero_value = reading["zero_value"]

        if self.lsb_value is None:
            self.lsb_value = 1.0
        if self.zero_value is None:
            self.zero_value = 0.0

    def _decode(self, obj, context, path):
        return obj * self.lsb_value + self.zero_value

    def _encode(self, obj, context, path):
        return round((obj - self.zero_value) / self.lsb_value)


class _SensorReadingTimestampAdaptor(construct.Adapter):
    SCALE = 1e6

    def _decode(self, obj: int, _context, _path):
        return datetime.fromtimestamp(obj / self.SCALE)

    def _encode(self, obj: datetime, _context, _path):
        return int(obj.timestamp() * self.SCALE)


_timestamp_cons = _SensorReadingTimestampAdaptor(construct.Long)
_timestamp_cons_len = 8  # _timestamp_cons.sizeof()


def _generate_cons_for_reading(reading: SensorMetaReading):
    if reading["bits"] % 8 != 0:
        raise NotImplementedError(
            f"bits must be a multiple of 8, was {reading['bits']}. (Unaligned values are not implemented.)"
        )

    encoding = EncodingType(int(reading["encoding"]))
    if encoding == EncodingType.float:
        if reading["signed"] != True:
            raise ValueError('Do not set "signed" for float-type encoding')
        if reading["lsb_value"] != 1.0:
            raise ValueError('Do not set "lsb_value" for float-type encoding')
        if reading["zero_value"] != 0.0:
            raise ValueError('Do not set "zero_value" for float-type encoding')

        if reading["bits"] == 16:
            return construct.Float16b
        elif reading["bits"] == 32:
            return construct.Float32b
        elif reading["bits"] == 64:
            return construct.Float64b
        else:
            raise ValueError(
                f"Unsupported bit length {reading['bits']} for float, must be 16, 32, or 64"
            )

    elif encoding == EncodingType.bits_integer_scaled:
        integer = construct.BytesInteger(
            reading["bits"] // 8,
            signed=(reading["signed"] != False),
        )

        return _SensorReadingScalingAdaptor(reading, integer)

    elif encoding == EncodingType.timestamp:
        if reading["unit"] != "":
            raise ValueError('Do not set "unit" for timestamp encoding')
        if reading["signed"] != True:
            raise ValueError('Do not set "signed" for timestamp encoding')
        if reading["lsb_value"] != 1.0:
            raise ValueError('Do not set "lsb_value" for timestamp encoding')
        if reading["zero_value"] != 0.0:
            raise ValueError('Do not set "zero_value" for timestamp encoding')
        if reading["bits"] != 64:
            raise ValueError('Timestamp encoding must be 64 bits')

        return _timestamp_cons

    elif encoding == EncodingType.string:
        if reading["bits"] != 0:
            raise ValueError('Do not set "bits" for string-type encoding')
        if reading["signed"] != True:
            raise ValueError('Do not set "signed" for string-type encoding')
        if reading["lsb_value"] != 1.0:
            raise ValueError('Do not set "lsb_value" for string-type encoding')
        if reading["zero_value"] != 0.0:
            raise ValueError(
                'Do not set "zero_value" for string-type encoding')

        return _null_terminated_string

    else:
        raise ValueError(f"Unsupported encoding {encoding}")


class SensorEncoder:
    _meta_blob: bytes
    _meta_dict: SensorMeta
    _can_use_encode_raw: bool
    _cons: construct.Struct
    _cons_len: int

    def __init__(self, meta: Union[SensorMeta, bytes]) -> None:
        if type(meta) == bytes:
            self._meta_blob = meta
        elif type(meta) is dict:
            self._meta_blob = _sensor_meta_struct.build(meta)
        else:
            raise ValueError("Meta must be bytes or dict")

        self._meta_dict = _sensor_meta_struct.parse(self._meta_blob)

        if len(self._meta_dict["readings"]) == 0:
            self._can_use_encode_raw = False
            print("TIMESTAMP_ERROR: NOT ENOUGH READINGS")
        elif self._meta_dict["readings"][0]["name"] != "timestamp":
            self._can_use_encode_raw = False
            print("TIMESTAMP_ERROR: WRONG NAME")
        elif self._meta_dict["readings"][0]["unit"] != "":
            self._can_use_encode_raw = False
            print("TIMESTAMP_ERROR: WRONG UNIT")
        elif int(self._meta_dict["readings"][0]["encoding"]) != int(
                EncodingType.timestamp):
            self._can_use_encode_raw = False
            print("TIMESTAMP_ERROR: WRONG ENCODING")
        else:
            self._can_use_encode_raw = True

        reading_cons = (reading["name"] / _generate_cons_for_reading(reading)
                        for reading in self._meta_dict["readings"])

        self._cons = construct.Struct(*reading_cons)
        try:
            self._cons_len = self._cons.sizeof()
        except construct.SizeofError:
            self._cons_len = None  # Length is dynamic

    @property
    def meta_blob(self) -> bytes:
        return self._meta_blob

    @property
    def meta_dict(self) -> SensorMeta:
        return self._meta_dict

    @property
    def length_bytes(self) -> int:
        return self._cons_len

    def encode(self, timestamp=None, **kwargs) -> bytes:
        if timestamp == None:
            timestamp = datetime.now()

        kwargs["timestamp"] = timestamp

        return self._cons.build(kwargs)

    def encode_raw(self, data: bytes, timestamp=None) -> bytes:
        if timestamp == None:
            timestamp = datetime.now()

        if not self._can_use_encode_raw:
            raise ValueError(
                "This encoding does not support encode_raw. In order to support encode_raw, it's first reading must be TimestampReading"
            )

        # If the data size is dynamic (i.e. strings), this is not checked
        _cons_len_no_ts = self._cons_len - _timestamp_cons_len
        if self._cons_len != None and len(data) != _cons_len_no_ts:
            raise ValueError(
                f"Raw data should be {_cons_len_no_ts} bytes, is {len(data)} bytes"
            )

        return _timestamp_cons.build(timestamp) + data

    def decode(self, data: bytes) -> dict:
        return self._cons.parse(data)
