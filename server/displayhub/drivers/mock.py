class MockDisplay:
    def __init__(self, display_id: str, width: int = 16, height: int = 2):
        self.display_id = display_id
        self.width = width
        self.height = height
        self.lines = [""] * height

    def init(self):
        print(f"[mock:{self.display_id}] init {self.width}x{self.height}", flush=True)

    def clear(self):
        self.lines = [""] * self.height
        print(f"[mock:{self.display_id}] clear", flush=True)

    def write_lines(self, lines):
        clean_lines = []
        for i in range(self.height):
            line = str(lines[i]) if i < len(lines) else ""
            clean_lines.append(line[: self.width].ljust(self.width))

        self.lines = clean_lines
        print(f"[mock:{self.display_id}]", flush=True)
        for line in self.lines:
            print(f"|{line}|", flush=True)

    def info(self):
        return {
            "id": self.display_id,
            "driver": "mock",
            "width": self.width,
            "height": self.height,
        }
