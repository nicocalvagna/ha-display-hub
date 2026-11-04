#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/ha-display-hub"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_USER="${SUDO_USER:-$(id -un)}"

if [[ "$SERVICE_USER" == "root" ]]; then
  echo "Ejecutá este instalador como usuario habitual (sin sudo): ./install.sh" >&2
  exit 1
fi

# Copy application files, keeping an existing config.yaml untouched.
sudo install -d "$APP_DIR" "$APP_DIR/systemd"
sudo cp -R "$SRC_DIR/server" "$APP_DIR/"
sudo cp -R "$SRC_DIR/examples" "$APP_DIR/"
sudo install -m 644 "$SRC_DIR/requirements.txt" "$APP_DIR/requirements.txt"
sudo install -m 644 "$SRC_DIR/setup.py" "$APP_DIR/setup.py"
sudo install -m 755 "$SRC_DIR/setup.sh" "$APP_DIR/setup.sh"

if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
  sudo python3 -m venv "$APP_DIR/.venv"
fi
sudo "$APP_DIR/.venv/bin/python" -m pip install -r "$APP_DIR/requirements.txt"

if [[ ! -e "$APP_DIR/config.yaml" ]]; then
  sudo cp "$APP_DIR/examples/config.yaml" "$APP_DIR/config.yaml"
fi

# Adapt the service user (the original unit assumes 'nicolas').
sed "s/^User=.*/User=${SERVICE_USER}/" "$SRC_DIR/systemd/ha-display-hub.service" | \
  sudo tee /etc/systemd/system/ha-display-hub.service >/dev/null
sudo systemctl daemon-reload

# Allow the service account to open /dev/i2c-* (effective for the next service start).
if getent group i2c >/dev/null; then
  sudo usermod -aG i2c "$SERVICE_USER"
fi

echo "Servidor instalado en $APP_DIR (config.yaml conservado)."
if [[ -t 0 && -t 1 ]]; then
  if command -v whiptail >/dev/null 2>&1; then
    read -r -p '¿Abrir ahora el configurador interactivo? [S/n] ' answer
    if [[ "${answer,,}" != "n" ]]; then
      sudo "$APP_DIR/setup.sh"
    fi
  else
    echo "Falta whiptail para usar el asistente: sudo apt install whiptail i2c-tools"
  fi
fi
printf '\nPara volver al configurador: sudo %s/setup.sh\n' "$APP_DIR"
printf 'Para iniciar automáticamente el servidor: sudo systemctl enable --now ha-display-hub\n'
