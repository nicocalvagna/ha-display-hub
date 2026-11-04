#!/usr/bin/env python3
"""Interactive, terminal-based configuration utility for HA Display Hub.

Uses whiptail (like raspi-config), PyYAML, and the optional i2cdetect tool.
Run with: sudo /opt/ha-display-hub/setup.sh
"""

from __future__ import annotations

import argparse
import copy
import glob
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unicodedata

import yaml


APP_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = APP_DIR / "config.yaml"
SERVICE = "ha-display-hub"
REAL_DRIVER = "hd44780_i2c"
DRIVERS = (REAL_DRIVER, "mock")


class HexAddress(int):
    """Write adapter addresses as 0x27 instead of 39 in YAML."""


def _hex_representer(dumper, address):
    return dumper.represent_scalar("tag:yaml.org,2002:int", f"0x{int(address):02x}")


yaml.SafeDumper.add_representer(HexAddress, _hex_representer)


def int_value(value):
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return int(str(value).strip(), 0)


def load_config(path):
    if not path.exists():
        return {"server": {"listen": "0.0.0.0", "port": 4510}, "displays": []}
    with path.open(encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError("config.yaml debe contener un objeto YAML.")
    data.setdefault("server", {"listen": "0.0.0.0", "port": 4510})
    data.setdefault("displays", [])
    if not isinstance(data["server"], dict) or not isinstance(data["displays"], list):
        raise ValueError("Las secciones server y displays tienen formato incorrecto.")
    return data


def validate(config):
    server = config.get("server", {})
    if not isinstance(server, dict):
        raise ValueError("server debe ser un objeto.")
    listen = server.get("listen", "0.0.0.0")
    if not isinstance(listen, str) or not listen.strip():
        raise ValueError("La dirección de escucha no puede estar vacía.")
    port = int_value(server.get("port", 4510))
    if not 1 <= port <= 65535:
        raise ValueError("El puerto debe estar entre 1 y 65535.")
    seen_ids, seen_addresses = set(), set()
    for index, item in enumerate(config.get("displays", []), 1):
        if not isinstance(item, dict):
            raise ValueError(f"Display {index}: formato incorrecto.")
        name = item.get("id")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Display {index}: identificador vacío.")
        if name in seen_ids:
            raise ValueError(f"Identificador duplicado: {name}.")
        seen_ids.add(name)
        driver = item.get("driver", "mock")
        if driver not in DRIVERS:
            raise ValueError(f"{name}: driver desconocido ({driver}).")
        width, height = int_value(item.get("width", 16)), int_value(item.get("height", 2))
        if not 1 <= width <= 40 or not 1 <= height <= 4:
            raise ValueError(f"{name}: dimensiones fuera de rango (ancho 1-40, alto 1-4).")
        if driver == REAL_DRIVER:
            bus = int_value(item.get("bus", 1))
            if not 0 <= bus <= 255:
                raise ValueError(f"{name}: bus I²C fuera de rango.")
            if "address" not in item:
                raise ValueError(f"{name}: falta la dirección I²C.")
            address = int_value(item["address"])
            if not 0x03 <= address <= 0x77:
                raise ValueError(f"{name}: dirección I²C inválida.")
            key = (bus, address)
            if key in seen_addresses:
                raise ValueError(f"Dos displays usan bus {bus}, dirección 0x{address:02x}.")
            seen_addresses.add(key)
    return True


def save_config(path, config):
    validate(config)
    output = copy.deepcopy(config)
    for item in output["displays"]:
        if item.get("driver") == REAL_DRIVER:
            item["address"] = HexAddress(int_value(item["address"]))
            item["bus"] = int_value(item.get("bus", 1))
        item["width"] = int_value(item.get("width", 16))
        item["height"] = int_value(item.get("height", 2))
    output["server"]["port"] = int_value(output["server"].get("port", 4510))
    content = yaml.safe_dump(output, sort_keys=False, allow_unicode=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = path.stat() if path.exists() else None
    handle, tempname = tempfile.mkstemp(prefix=".config-", suffix=".yaml", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as target:
            target.write(content)
            target.flush()
            os.fsync(target.fileno())
        if previous:
            os.chmod(tempname, previous.st_mode & 0o777)
            if os.geteuid() == 0:
                os.chown(tempname, previous.st_uid, previous.st_gid)
            shutil.copy2(path, path.with_name(path.name + ".bak"))
        else:
            os.chmod(tempname, 0o644)
        os.replace(tempname, path)
    finally:
        if os.path.exists(tempname):
            os.unlink(tempname)


def scan_addresses(bus):
    if not shutil.which("i2cdetect"):
        raise RuntimeError("Falta i2c-tools. Instalá: sudo apt install i2c-tools")
    proc = subprocess.run(["i2cdetect", "-y", str(bus)], capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError((proc.stderr or proc.stdout).strip() or "Falló i2cdetect")
    found = set()
    occupied = 0
    for line in proc.stdout.splitlines():
        if not re.match(r"^[0-7][0-9a-fA-F]:", line):
            continue
        for token in line.split(":", 1)[1].split():
            if token == "UU":
                occupied += 1
            elif re.fullmatch(r"[0-7][0-9a-fA-F]", token):
                found.add(int(token, 16))
    return sorted(found), occupied


def next_id(displays):
    existing = {item.get("id") for item in displays}
    n = 1
    while f"rack{n}" in existing:
        n += 1
    return f"rack{n}"


def adapter_candidate(address):
    # PCF8574/PCF8574A; never assume other I²C addresses are LCD adapters.
    return 0x20 <= address <= 0x27 or 0x38 <= address <= 0x3F


def display_label(item):
    label = f'{item.get("id", "?")}: {item.get("driver", "mock")}'
    if item.get("driver") == REAL_DRIVER:
        label += f' bus {item.get("bus", 1)} / 0x{int_value(item.get("address", 0)):02x}'
    return label + f' / {item.get("width", 16)}x{item.get("height", 2)}'



def menu_text(value):
    """Evita que whiptail/newt recorte opciones al encontrar caracteres UTF-8."""
    return unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")


class Dialog:
    def __init__(self):
        if not shutil.which("whiptail"):
            raise RuntimeError("Falta whiptail. Instalá: sudo apt install whiptail")

    def call(self, kind, title, message, *options):
        args = ["whiptail", "--backtitle", "HA Display Hub | Configuración",
                "--title", title, kind, message, "20", "76"]
        if kind in ("--menu", "--checklist"):
            args.append("10")
        args.extend(str(x) for x in options)
        # whiptail dibuja su interfaz en stdout y devuelve la selección en stderr.
        # Capturar stdout ocultaría los menús y parecería que quedó congelado.
        proc = subprocess.run(args, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            return None
        return proc.stderr.strip()

    def info(self, message, title="Información"):
        self.call("--msgbox", title, message)

    def yes(self, message, title="Confirmar"):
        return self.call("--yesno", title, message) is not None

    def ask(self, message, value="", title="Editar"):
        return self.call("--inputbox", title, message, value)

    def menu(self, title, message, items):
        options = [part for tag, label in items for part in (tag, menu_text(label))]
        return self.call("--menu", title, message, *options)

    def checklist(self, title, message, items):
        options = [part for tag, label, state in items
                   for part in (tag, menu_text(label), state)]
        output = self.call("--checklist", title, message, *options)
        return None if output is None else shlex.split(output)


class Wizard:
    def __init__(self, path, dialog):
        self.path, self.dialog = path, dialog
        self.data = load_config(path)
        self.dirty = False

    @property
    def displays(self):
        return self.data["displays"]

    def summary(self):
        server = self.data["server"]
        content = f'Escucha: {server.get("listen", "0.0.0.0")}:{server.get("port", 4510)}\n\n'
        content += "Displays:\n"
        content += "\n".join("  " + display_label(item) for item in self.displays) or "  (ninguno)"
        self.dialog.info(content, "Configuración actual")

    def server_options(self):
        while True:
            server = self.data["server"]
            option = self.dialog.menu("Servidor", "Elegí qué modificar:", [
                ("ip", f'Dirección de escucha: {server.get("listen", "0.0.0.0")}'),
                ("port", f'Puerto TCP: {server.get("port", 4510)}'),
            ])
            if option is None:
                return
            if option == "ip":
                value = self.dialog.ask("IP de escucha (ej.: 192.168.88.141 o 0.0.0.0):",
                                        str(server.get("listen", "0.0.0.0")))
                if value is not None and value.strip():
                    server["listen"] = value.strip()
                    self.dirty = True
            if option == "port":
                value = self.dialog.ask("Puerto TCP (1 a 65535):", str(server.get("port", 4510)))
                if value is not None:
                    try:
                        port = int_value(value)
                        if not 1 <= port <= 65535:
                            raise ValueError()
                        server["port"] = port
                        self.dirty = True
                    except ValueError:
                        self.dialog.info("Puerto inválido.", "Error")

    def available_buses(self):
        buses = []
        for device in glob.glob("/dev/i2c-*"):
            try:
                buses.append(int(device.rsplit("-", 1)[1]))
            except ValueError:
                continue
        return sorted(set(buses)) or [1]

    def select_bus(self):
        buses = self.available_buses()
        selected = self.dialog.menu("Bus I²C", "Elegí el bus que querés examinar:",
                                    [(str(bus), f"/dev/i2c-{bus}") for bus in buses])
        return None if selected is None else int(selected)

    def discover(self):
        bus = self.select_bus()
        if bus is None:
            return
        if not self.dialog.yes("Se ejecutará i2cdetect sobre el bus elegido. El escaneo puede "
                               "interferir con ciertos dispositivos I²C. ¿Continuar?", "Escanear I²C"):
            return
        try:
            found, occupied = scan_addresses(bus)
        except (OSError, RuntimeError) as exc:
            self.dialog.info(str(exc), "No se pudo escanear")
            return
        if not found:
            self.dialog.info(f"No hay direcciones detectadas en bus {bus}. "
                             f"Direcciones ocupadas por drivers: {occupied}.", "Escaneo")
        else:
            current = {(int_value(x.get("bus", 1)), int_value(x["address"]))
                       for x in self.displays if x.get("driver") == REAL_DRIVER}
            entries = []
            for address in found:
                if (bus, address) in current:
                    status = "configurado"
                elif adapter_candidate(address):
                    status = "posible PCF8574"
                else:
                    status = "otro I²C (no LCD)"
                entries.append(f"0x{address:02x} - {status}")
            self.dialog.info(f"Bus {bus}:\n" + "\n".join(entries) +
                             (f"\nDispositivos ocupados (UU): {occupied}" if occupied else ""),
                             "Resultados I²C")
            candidates = [address for address in found if adapter_candidate(address)
                          and (bus, address) not in current]
            if candidates:
                selected = self.dialog.checklist(
                    "Agregar LCD", "Marcá las direcciones de adaptadores PCF8574 que querés agregar "
                    "(se crearán con 16x2 y nombres rackN):",
                    [(f"{address:02x}", f"bus {bus} / 0x{address:02x}", "OFF") for address in candidates])
                if selected:
                    for selected_address in selected:
                        address = int(selected_address, 16)
                        self.displays.append({"id": next_id(self.displays), "driver": REAL_DRIVER,
                                              "bus": bus, "address": address,
                                              "width": 16, "height": 2})
                    self.dirty = True
                    self.dialog.info(f"Se agregaron {len(selected)} display(s). "
                                     "Podés ajustar sus tamaños en Editar display.")
        missing = [(index, item) for index, item in enumerate(self.displays)
                   if item.get("driver") == REAL_DRIVER and int_value(item.get("bus", 1)) == bus
                   and int_value(item["address"]) not in found]
        if missing and self.dialog.yes("Hay LCD configurados que no respondieron al escaneo. "
                                      "¿Querés revisar cuáles quitar?", "No detectados"):
            selected = self.dialog.checklist("Quitar LCD", "Marcá los que querés quitar:",
                                             [(item["id"], display_label(item), "OFF")
                                              for _, item in missing])
            if selected and self.dialog.yes("¿Eliminar los displays seleccionados de la configuración?"):
                self.data["displays"] = [item for item in self.displays if item["id"] not in selected]
                self.dirty = True

    def select_display(self):
        if not self.displays:
            self.dialog.info("No hay displays configurados.")
            return None
        choice = self.dialog.menu("Displays", "Seleccioná un display:",
                                  [(item["id"], display_label(item)) for item in self.displays])
        return next((item for item in self.displays if item["id"] == choice), None)

    def manual_add(self):
        item = {"id": next_id(self.displays), "driver": REAL_DRIVER,
                "bus": 1, "address": 0x27, "width": 16, "height": 2}
        result = self.edit_fields(item, creating=True)
        if result:
            self.displays.append(item)
            self.dirty = True

    def edit_fields(self, item, creating=False):
        if creating:
            name = self.dialog.ask("Identificador único usado por Home Assistant:", item["id"], "Nuevo LCD")
            if name is None:
                return False
            if not name.strip() or any(x["id"] == name.strip() for x in self.displays):
                self.dialog.info("El identificador está vacío o ya existe.", "Error")
                return False
            item["id"] = name.strip()
        while True:
            option = self.dialog.menu("Editar display", display_label(item) + "\nElegí qué modificar:", [
                ("id", f'Identificador: {item.get("id")}'),
                ("driver", f'Driver: {item.get("driver", "mock")}'),
                ("bus", f'Bus I²C: {item.get("bus", 1)}'),
                ("address", f'Dirección: 0x{int_value(item.get("address", 0x27)):02x}'),
                ("width", f'Columnas: {item.get("width", 16)}'),
                ("height", f'Filas: {item.get("height", 2)}'),
                ("done", "Terminar edición"),
            ])
            if option is None or option == "done":
                return True
            if option == "driver":
                new_driver = self.dialog.menu("Driver", "Elegí controlador:",
                                              [(REAL_DRIVER, "LCD HD44780 / PCF8574"),
                                               ("mock", "Simulación (sin hardware)")])
                if new_driver is not None:
                    item["driver"] = new_driver
                    item.setdefault("bus", 1)
                    item.setdefault("address", 0x27)
                    self.dirty = True
                continue
            default = str(item.get(option, ""))
            if option == "address":
                default = f'0x{int_value(item.get("address", 0x27)):02x}'
            entry = self.dialog.ask(f'Nuevo valor de {option} (direcciones: 0x27 o decimal 39):',
                                    default, "Editar valor")
            if entry is None:
                continue
            try:
                if option == "id":
                    if not entry.strip() or any(x is not item and x["id"] == entry.strip()
                                                    for x in self.displays):
                        raise ValueError("Identificador vacío o duplicado.")
                    item["id"] = entry.strip()
                elif option in ("bus", "address", "width", "height"):
                    number = int_value(entry)
                    low, high = {"bus": (0, 255), "address": (3, 119),
                                 "width": (1, 40), "height": (1, 4)}[option]
                    if not low <= number <= high:
                        raise ValueError(f"Valor permitido: {low} a {high}.")
                    if option == "address" and not adapter_candidate(number):
                        if not self.dialog.yes("Dirección fuera de los rangos habituales "
                                               "PCF8574 (0x20-0x27, 0x38-0x3f). ¿Usarla igual?"):
                            continue
                    item[option] = number
                self.dirty = True
            except ValueError as exc:
                self.dialog.info(str(exc), "Valor inválido")

    def remove(self):
        item = self.select_display()
        if item and self.dialog.yes(f'¿Eliminar {display_label(item)} de la configuración?'):
            self.displays.remove(item)
            self.dirty = True

    def save(self, restart=False):
        try:
            save_config(self.path, self.data)
            self.dirty = False
        except (OSError, ValueError, yaml.YAMLError) as exc:
            self.dialog.info(str(exc), "Error al guardar")
            return
        if not restart:
            self.dialog.info(f"Configuración guardada en {self.path}.\n"
                             "Copia anterior: config.yaml.bak.\n\n"
                             "Para aplicar los cambios, reiniciá el servicio.", "Guardado")
            return
        service = subprocess.run(["systemctl", "restart", SERVICE], capture_output=True, text=True)
        if service.returncode:
            self.dialog.info(f"Guardado, pero no se pudo reiniciar el servicio:\n"
                             f"{service.stderr.strip()}\n\n"
                             f"Revisar: journalctl -u {SERVICE} -n 40", "Error")
        else:
            self.dialog.info("Configuración guardada y servicio reiniciado correctamente.", "Listo")

    def run(self):
        while True:
            choice = self.dialog.menu("HA Display Hub Setup", "Configuración de LCD y servidor TCP:", [
                ("1", "Ver configuración actual"),
                ("2", "Buscar I²C y agregar/quitar LCD"),
                ("3", "Agregar display manualmente"),
                ("4", "Editar display"),
                ("5", "Quitar display"),
                ("6", "IP y puerto del servidor"),
                ("7", "Guardar configuración"),
                ("8", "Guardar y reiniciar servicio"),
                ("9", "Salir"),
            ])
            if choice is None or choice == "9":
                if self.dirty and not self.dialog.yes("Hay cambios sin guardar. ¿Salir sin guardarlos?"):
                    continue
                return
            if choice == "1":
                self.summary()
            elif choice == "2":
                self.discover()
            elif choice == "3":
                self.manual_add()
            elif choice == "4":
                item = self.select_display()
                if item:
                    self.edit_fields(item)
            elif choice == "5":
                self.remove()
            elif choice == "6":
                self.server_options()
            elif choice == "7":
                self.save()
            elif choice == "8":
                self.save(restart=True)


def main():
    parser = argparse.ArgumentParser(description="Configurador de HA Display Hub")
    parser.add_argument("-c", "--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error("El asistente necesita una terminal interactiva (SSH o consola).")
    if os.geteuid() != 0:
        parser.error("Ejecutá con sudo: sudo ./setup.sh")
    try:
        Wizard(args.config, Dialog()).run()
    except (ValueError, OSError, yaml.YAMLError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
