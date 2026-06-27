import json
import socketserver
from typing import Dict, Any

from displayhub import __version__
from displayhub.config import load_config
from displayhub.drivers.mock import MockDisplay


class DisplayHub:
    def __init__(self, config: dict):
        self.config = config
        self.displays = {}
        self._load_displays()

    def _load_displays(self):
        for item in self.config.get("displays", []):
            display_id = item["id"]
            driver = item.get("driver", "mock")
            width = int(item.get("width", 16))
            height = int(item.get("height", 2))

            if driver != "mock":
                raise ValueError(f"Unsupported driver in this version: {driver}")

            display = MockDisplay(display_id, width, height)
            display.init()
            self.displays[display_id] = display

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        cmd = request.get("cmd")

        if cmd == "ping":
            return {"status": "ok", "message": "pong"}

        if cmd == "info":
            return {
                "status": "ok",
                "version": __version__,
                "displays": list(self.displays.keys()),
            }

        if cmd == "clear":
            target = request.get("target")
            display = self.displays.get(target)
            if not display:
                return {"status": "error", "error": "unknown display"}
            display.clear()
            return {"status": "ok"}

        if cmd == "display":
            target = request.get("target")
            display = self.displays.get(target)
            if not display:
                return {"status": "error", "error": "unknown display"}
            lines = request.get("lines", [])
            if not isinstance(lines, list):
                return {"status": "error", "error": "lines must be a list"}
            display.write_lines(lines)
            return {"status": "ok"}

        return {"status": "error", "error": "unknown command"}


class Handler(socketserver.StreamRequestHandler):
    hub: DisplayHub = None

    def handle(self):
        for raw_line in self.rfile:
            try:
                request = json.loads(raw_line.decode("utf-8"))
                response = self.hub.handle(request)
            except Exception as exc:
                response = {"status": "error", "error": str(exc)}

            self.wfile.write((json.dumps(response) + "\n").encode("utf-8"))


def run(config_path: str):
    config = load_config(config_path)
    server_cfg = config.get("server", {})
    listen = server_cfg.get("listen", "0.0.0.0")
    port = int(server_cfg.get("port", 4510))

    hub = DisplayHub(config)
    Handler.hub = hub

    with socketserver.ThreadingTCPServer((listen, port), Handler) as server:
        print(f"HA Display Hub listening on {listen}:{port}", flush=True)
        server.serve_forever()
