from .pcf8574 import PCF8574
from .hd44780 import HD44780


class HD44780I2C(HD44780):
    def __init__(self, address, bus=1, width=16, height=2):
        expander = PCF8574(address, bus)
        super().__init__(expander, width, height)
        self.address = address
        self.bus = bus

    def init(self):
        super().init()

    def close(self):
        self.expander.close()

    def info(self):
        info = super().info()
        info.update({
            "driver": "hd44780_i2c",
            "address": hex(self.address),
            "bus": self.bus,
        })
        return info

