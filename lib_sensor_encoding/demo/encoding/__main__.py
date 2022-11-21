# Replace with "from lib_sensor_encoding" for normal usage
from ... import TimestampReading, EncodingType, SensorEncoder
from datetime import datetime

# Utility Function
from hexdump import hexdump as _hexdump
def hexdump(data):
    print(f"({len(data)} bytes)")
    _hexdump(data)

def run_demo():
    print()
    print("CPU Temperature Sensor Example")
    print("==============================")
    print("Metadata")
    print("--------")
    # Encoders can be created from a dict describing their data.
    cpu_temp_encoder = SensorEncoder({
        "name": "CPU Temperature",
        "readings": [
            # An automatic timestamp can be added to each packet with TimestampReading
            TimestampReading,
            {
                # This is used for the dictionary keys for the encode and decode functions
                "name": "cpu_temp",
                # The unit is displayed to the user
                "unit": "°C",
                # This specifies how the sensor reading is encoded
                "encoding": EncodingType.float,
                "bits": 32,
            },
            {
                "name": "open_files",
                "encoding": EncodingType.bits_integer_scaled,
                "bits": 32,
                "signed": False
            },
            {
                "name": "status",
                "encoding": EncodingType.string
            }
        ],
    })
    print(cpu_temp_encoder.meta_dict)
    hexdump(cpu_temp_encoder.meta_blob)
    print()
    print("Sensor Reading")
    print("--------------")
    cpu_temp_data = cpu_temp_encoder.encode(cpu_temp=45.2, open_files=3412, status="chilling")
    print(cpu_temp_encoder.decode(cpu_temp_data))
    hexdump(cpu_temp_data)
    print()
    print()
    print()
    print()
    print("MPU 6050 Example")
    print("================")
    print("Metadata")
    print("--------")

    MPU6050AccelAxis = {
        "unit": "g",
        "encoding": EncodingType.bits_integer_scaled,
        "signed": True,
        "bits": 16,
        "lsb_value": 16 / 2**15,
    }

    MPU6050GyroAxis = {
        "unit": "°/s",
        "encoding": EncodingType.bits_integer_scaled,
        "signed": True,
        "bits": 16,
        "lsb_value": 2000 / 2**15,
    }

    mpu6050_encoder = SensorEncoder({
        "name":
        "MPU6050",
        "readings": [
            TimestampReading,
            # Python dict union syntax can be used to create multiple identical readings with different names
            { "name": "ax" } | MPU6050AccelAxis,
            { "name": "ay" } | MPU6050AccelAxis,
            { "name": "az" } | MPU6050AccelAxis,
            {
                "name": "temperature",
                "unit": "°C",
                "encoding": EncodingType.bits_integer_scaled,
                "bits": 16,
                "lsb_value": 1 / 340,
                "zero_value": 36.53
            },
            { "name": "gx" } | MPU6050GyroAxis,
            { "name": "gy" } | MPU6050GyroAxis,
            { "name": "gz" } | MPU6050GyroAxis,
        ],
    })
    print(mpu6050_encoder.meta_dict)
    hexdump(mpu6050_encoder.meta_blob)

    # Encoders can also be created directly from a binary blob
    mpu6050_encoder = SensorEncoder(mpu6050_encoder.meta_blob)

    print()
    print("Sensor Reading")
    print("--------------")
    # The timestamp can be overridden if you know a more accurate timestamp than the default datetime.now()
    mpu6050_data = mpu6050_encoder.encode(timestamp=datetime(2022, 11, 20, 1, 11, 15), ax=0.98, ay=0.01, az=-0.05, temperature=24.5, gx=10.1, gy=-20.4, gz=5.2)
    print(mpu6050_encoder.decode(mpu6050_data))
    hexdump(mpu6050_data)
    print()
    print("Sensor Reading (raw)")
    print("--------------------")
    # Because the format of this packet *exactly* matches the binary format of the MPU6050,
    # and it's first reading is TimestampReading, we can use encode_raw
    # This bypasses any scaling or conversions, and many internal checks, so use with care!
    # Notice how the exact bytes here are included in the output (after the 8 timestamp bytes)
    mpu6050_data_raw = mpu6050_encoder.encode_raw(bytes.fromhex("0716018bfca2fdd2ffd2fdce005d"))
    print(mpu6050_encoder.decode(mpu6050_data_raw))
    hexdump(mpu6050_data_raw)
    print()

if __name__ == "__main__":
    run_demo()
