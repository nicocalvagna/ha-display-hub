from .mock import MockDisplay
from .hd44780_i2c import HD44780I2C


class DriverFactory:

    @staticmethod
    def create(config):

        driver = config.get("driver", "mock")

        if driver == "mock":
            return MockDisplay(
                config["id"],
                config.get("width", 16),
                config.get("height", 2)
            )

        if driver == "hd44780_i2c":
            return HD44780I2C(
                address=int(config["address"]),
                bus=int(config.get("bus", 1)),
                width=int(config.get("width", 16)),
                height=int(config.get("height", 2))
            )

        raise ValueError(f"Unknown driver '{driver}'")
