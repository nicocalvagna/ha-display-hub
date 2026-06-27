#!/usr/bin/env bash
set -e

APP_DIR="/opt/ha-display-hub"

sudo mkdir -p "$APP_DIR"
sudo cp -r . "$APP_DIR"
sudo python3 -m venv "$APP_DIR/.venv"
sudo "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

if [ ! -f "$APP_DIR/config.yaml" ]; then
  sudo cp "$APP_DIR/examples/config.yaml" "$APP_DIR/config.yaml"
fi

sudo cp "$APP_DIR/systemd/ha-display-hub.service" /etc/systemd/system/ha-display-hub.service
sudo systemctl daemon-reload

echo "Installed. Edit $APP_DIR/config.yaml, then run:"
echo "sudo systemctl enable --now ha-display-hub"
