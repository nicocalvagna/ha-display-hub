import time


class HD44780:
    ENABLE = 0x04
    RW = 0x02
    RS = 0x01
    BACKLIGHT = 0x08

    def __init__(self, expander, width=16, height=2, backlight=True):
        self.expander = expander
        self.width = width
        self.height = height
        self.backlight = self.BACKLIGHT if backlight else 0x00
        self.framebuffer = [" " * width for _ in range(height)]

    def _write4bits(self, data):
        self.expander.write(data | self.backlight)
        self.expander.write(data | self.ENABLE | self.backlight)
        time.sleep(0.0005)
        self.expander.write((data & ~self.ENABLE) | self.backlight)
        time.sleep(0.0001)

    def _send(self, value, mode=0):
        high = value & 0xF0
        low = (value << 4) & 0xF0
        self._write4bits(high | mode)
        self._write4bits(low | mode)

    def command(self, value):
        self._send(value, 0)
        time.sleep(0.002)

    def write_char(self, char):
        self._send(ord(char), self.RS)

    def init(self):
        time.sleep(0.05)

        self._write4bits(0x30)
        time.sleep(0.005)
        self._write4bits(0x30)
        time.sleep(0.005)
        self._write4bits(0x30)
        time.sleep(0.005)
        self._write4bits(0x20)

        self.command(0x28)  # 4-bit, 2 lines, 5x8
        self.command(0x08)  # display off
        self.clear()
        self.command(0x06)  # entry mode
        self.command(0x0C)  # display on, cursor off

    def clear(self):
        self.command(0x01)
        time.sleep(0.003)
        self.framebuffer = [" " * self.width for _ in range(self.height)]

    def _set_cursor(self, col, row):
        row_offsets = [0x00, 0x40, 0x14, 0x54]
        row = max(0, min(row, self.height - 1))
        col = max(0, min(col, self.width - 1))
        self.command(0x80 | (col + row_offsets[row]))

    def write_at(self, col, row, text):
        text = str(text)
        for i, ch in enumerate(text):
            x = col + i
            if x >= self.width:
                break
            if row >= self.height:
                break
            self._set_cursor(x, row)
            self.write_char(ch)

    def render(self, lines):
        new_framebuffer = []

        for row in range(self.height):
            line = str(lines[row]) if row < len(lines) else ""
            line = line[:self.width].ljust(self.width)
            new_framebuffer.append(line)

        for row in range(self.height):
            old = self.framebuffer[row]
            new = new_framebuffer[row]

            for col, ch in enumerate(new):
                if old[col] != ch:
                    self._set_cursor(col, row)
                    self.write_char(ch)

        self.framebuffer = new_framebuffer

    def write_lines(self, lines):
        self.render(lines)

    def info(self):
        return {
            "driver": "hd44780",
            "width": self.width,
            "height": self.height,
        }
