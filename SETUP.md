# Configuración interactiva de HA Display Hub

El proyecto incluye un asistente de terminal con menús `whiptail`, similar a `raspi-config`, para configurar los displays HD44780 con PCF8574.

## Dependencias del sistema

```bash
sudo apt update
sudo apt install -y git python3-venv whiptail i2c-tools
sudo raspi-config nonint do_i2c 0
```

Habilitar el bus I²C puede requerir un reinicio. El instalador instala PyYAML y `smbus2` en un entorno virtual exclusivo.

## Instalación nueva

```bash
git clone https://github.com/nicocalvagna/ha-display-hub.git
cd ha-display-hub
./install.sh
```

El instalador propone ejecutar el asistente si detecta una terminal interactiva.

## Abrir el asistente en cualquier momento

```bash
sudo /opt/ha-display-hub/setup.sh
```

Opciones del menú:

1. Mostrar la configuración actual.
2. Escanear un bus I²C; seleccionar explícitamente qué adaptadores agregar y qué configuraciones ausentes quitar.
3. Agregar un LCD manualmente.
4. Cambiar ID (`rack1`, etc.), driver (`hd44780_i2c` o `mock`), bus, dirección, columnas y filas.
5. Quitar un display.
6. Configurar la IP de escucha del servidor y su puerto TCP.
7. Guardar la configuración.
8. Guardar y reiniciar únicamente `ha-display-hub.service`.
9. Salir (advierte si hay cambios sin guardar).

La búsqueda utiliza `i2cdetect` y **no altera los displays hasta confirmar y guardar**. El escaneo I²C puede interferir con ciertos dispositivos: el asistente pide confirmación antes de escanear. Solo propone como posibles adaptadores LCD las direcciones habituales PCF8574 (`0x20`–`0x27`) y PCF8574A (`0x38`–`0x3f`). La detección de una dirección **no certifica que sea un PCF8574**, por lo que es necesario verificar el hardware. Dispositivos como `0x48` se muestran, pero no se agregan automáticamente como LCD.

Los nuevos LCD se crean por defecto con 16 columnas y 2 filas, asignando el primer ID `rackN` libre. Se admiten dimensiones de 1–40 columnas y 1–4 filas; probar la geometría específica de cada controlador (20x4 es experimental en esta implementación).

Los cambios se guardan de forma atómica en `/opt/ha-display-hub/config.yaml` y se genera `/opt/ha-display-hub/config.yaml.bak` antes de sobrescribir el anterior. Se conservan los ajustes no gestionados por el asistente, aunque se normaliza el formato YAML y se pierden comentarios. Si se modifica un identificador (`rack1` a otro), hay que modificarlo también en el complemento Display Hub Client de Home Assistant.

El instalador **conserva el archivo `/opt/ha-display-hub/config.yaml` existente** y no reinicia servicios de LTE, MQTT ni Tailscale.

## Ejecutar el servicio

```bash
sudo systemctl enable --now ha-display-hub
systemctl status ha-display-hub --no-pager
```

Prueba del protocolo TCP:

```bash
echo '{"cmd":"info"}' | nc -w 2 192.168.88.141 4510
```

La IP y el puerto son ejemplos: ajustarlos a la configuración del servidor. En una Raspberry que también expone una conexión LTE, se recomienda escuchar solo en la IP LAN (por ejemplo `192.168.88.141`) en lugar de `0.0.0.0`, y no redirigir el puerto 4510 desde Internet. El servidor TCP no implementa autenticación.

## Pruebas locales

```bash
python3 -m unittest discover -s tests -v
```
