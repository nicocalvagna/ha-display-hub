import time

try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus


class PCF8574:
    def __init__(self, address: int, bus: int = 1):
        self.address = address
        self.bus_number = bus
        self.bus = SMBus(bus)

    def write(self, value: int):
        self.bus.write_byte(self.address, value & 0xFF)
        time.sleep(0.0001)

    def close(self):
        try:
            self.bus.close()
        except Exception:
            pass
