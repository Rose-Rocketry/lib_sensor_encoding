from .. import MQTTSensorClient, SensorMeta
from sty import fg, ef
import logging

sty_id = lambda x: fg.li_blue + ef.bold + x + ef.rs + fg.rs
sty_str = lambda x: fg.green + x + fg.rs
sty_num = lambda x: fg.yellow + str(x) + fg.rs


def print_sensor_data(id: str, meta: SensorMeta, data: tuple):
    print(sty_id(id) + " " + sty_str(repr(meta["name"])) + ":")

    for ch_meta, ch_data in zip(meta["channels"], data):
        print("    " + sty_str(ch_meta["name"]) + ": ", end="")

        if ch_meta["type"] == "timestamp":
            print(ch_data.to_datetime())
        elif ch_meta["type"] == "vector":
            print()
            for co_id, co_data in zip(ch_meta["components"], ch_data):
                print("      " + sty_id(co_id) + ": " + sty_num(co_data), end="")

                if "unit" in ch_meta:
                    print(" " + sty_str(ch_meta["unit"]))
                else:
                    print()
        else:
            print(sty_num(repr(ch_data)), end="")

            if "unit" in ch_meta:
                print(" " + sty_str(ch_meta["unit"]))
            else:
                print()

    print()


def main():
    logging.basicConfig(level=logging.INFO)

    client = MQTTSensorClient()
    client.subscribe_all_sensors()
    client.on_sensor_data = print_sensor_data
    client.run_foreground()


if __name__ == "__main__":
    main()
