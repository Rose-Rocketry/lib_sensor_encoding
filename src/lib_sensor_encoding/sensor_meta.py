import construct
import enum
from typing import Optional, TypedDict

_null_terminated_string = construct.NullTerminated(construct.GreedyString("utf8"))


class EncodingType(enum.IntEnum):
    timestamp = 0x00
    float = 0x01
    bits_integer_scaled = 0x02
    string = 0x03


_sensor_meta_struct = construct.Struct(
    "version" / construct.Const(0x01, construct.Byte),
    "name" / _null_terminated_string,
    "readings" / construct.PrefixedArray(
        construct.Int8ub,
        construct.Prefixed(
            construct.Int8ub,
            construct.Struct(
                "name" / _null_terminated_string,
                "unit" / construct.Default(_null_terminated_string, ""),
                "encoding" / construct.Enum(construct.Byte, EncodingType),
                "bits" / construct.Default(construct.Int8ub, 0),
                "signed" / construct.Default(construct.Flag, True),
                "lsb_value" / construct.Default(construct.Double, 1.0),
                "zero_value" / construct.Default(construct.Double, 0.0),
                construct.Terminated,
            ),
        )),
    construct.Terminated,
)


class SensorMetaReading(TypedDict):
    name: str
    unit: str
    encoding: EncodingType
    bits: Optional[int]
    signed: Optional[bool]
    lsb_value: Optional[float]
    zero_value: Optional[float]


class SensorMeta(TypedDict):
    name: str
    readings: list[SensorMetaReading]


TimestampReading: SensorMetaReading = {
    "name": "timestamp",
    "encoding": EncodingType.timestamp,
    "bits": 64,
}
