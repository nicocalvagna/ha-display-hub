"""Run: python3 -m unittest discover -s tests -v"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import setup as ds


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "server": {"listen": "192.168.88.141", "port": 4510, "extra": "kept"},
            "displays": [
                {"id": "rack1", "driver": "hd44780_i2c", "bus": 1,
                 "address": 0x27, "width": 16, "height": 2},
                {"id": "rack2", "driver": "hd44780_i2c", "bus": 1,
                 "address": 0x23, "width": 20, "height": 4},
            ],
            "unknown_option": "keep me",
        }

    def test_save_round_trip_backup(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.yaml"
            ds.save_config(p, self.config)
            text = p.read_text()
            self.assertIn("address: 0x27", text)
            self.assertIn("address: 0x23", text)
            loaded = ds.load_config(p)
            self.assertEqual(loaded["displays"][1]["width"], 20)
            self.assertEqual(loaded["unknown_option"], "keep me")
            loaded["server"]["port"] = 4511
            ds.save_config(p, loaded)
            self.assertEqual(ds.load_config(p)["server"]["port"], 4511)
            self.assertEqual(ds.load_config(Path(d) / "config.yaml.bak")["server"]["port"], 4510)

    def test_no_duplicate_addresses(self):
        self.config["displays"][1]["address"] = 0x27
        with self.assertRaisesRegex(ValueError, "Dos displays"):
            ds.validate(self.config)

    def test_driver_mock_can_have_no_i2c(self):
        self.config["displays"] = [{"id": "mock1", "driver": "mock", "width": 16, "height": 2}]
        self.assertTrue(ds.validate(self.config))

    def test_find_next_id(self):
        self.assertEqual(ds.next_id(self.config["displays"]), "rack3")

    def test_adapter_candidates(self):
        self.assertTrue(ds.adapter_candidate(0x23))
        self.assertTrue(ds.adapter_candidate(0x27))
        self.assertTrue(ds.adapter_candidate(0x3F))
        self.assertFalse(ds.adapter_candidate(0x48))

    def test_scan_output(self):
        output = """     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- --
20: -- -- -- 23 -- 25 26 27 -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- 48 -- -- -- -- -- -- --
"""
        with patch.object(ds.shutil, "which", return_value="/usr/sbin/i2cdetect"), \
             patch.object(ds.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, output, "")):
            addresses, busy = ds.scan_addresses(1)
            self.assertEqual(addresses, [0x23, 0x25, 0x26, 0x27, 0x48])
            self.assertEqual(busy, 0)

    def test_whiptail_uses_visible_terminal_output(self):
        # stdout debe seguir conectado a la terminal para mostrar el menú.
        with patch.object(ds.shutil, "which", return_value="/usr/bin/whiptail"), \
             patch.object(ds.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "rack1")) as run:
            selected = ds.Dialog().menu("LCD", "Elegí un display", [("rack1", "Display 1")])
            self.assertEqual(selected, "rack1")
            args, kwargs = run.call_args
            self.assertNotIn("--output-fd", args[0])
            self.assertNotIn("stdout", kwargs)
            self.assertEqual(kwargs["stderr"], subprocess.PIPE)


    def test_menu_labels_avoid_unicode_truncation(self):
        self.assertEqual(ds.menu_text("Ver configuración"), "Ver configuracion")
        self.assertEqual(ds.menu_text("Buscar I²C y agregar/quitar LCD"),
                         "Buscar I2C y agregar/quitar LCD")
        with patch.object(ds.shutil, "which", return_value="/usr/bin/whiptail"), \
             patch.object(ds.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "1")) as run:
            ds.Dialog().menu("Menú", "Elegí:", [("1", "Ver configuración")])
            args, _kwargs = run.call_args
            self.assertIn("Ver configuracion", args[0])
            self.assertNotIn("Ver configuración", args[0])
        with patch.object(ds.shutil, "which", return_value="/usr/bin/whiptail"), \
             patch.object(ds.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", '"27"')) as run:
            ds.Dialog().checklist("I²C", "Elegí:", [("27", "Dirección I²C: 0x27", "OFF")])
            args, _kwargs = run.call_args
            self.assertIn("Direccion I2C: 0x27", args[0])

    def test_invalid_ports(self):
        self.config["server"]["port"] = 0
        with self.assertRaisesRegex(ValueError, "puerto"):
            ds.validate(self.config)


if __name__ == "__main__":
    unittest.main()
