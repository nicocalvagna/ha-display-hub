# HA Display Hub

A lightweight multi-display server for Raspberry Pi and Linux devices.

It exposes a simple TCP/JSON protocol so Home Assistant or any other client can control multiple physical displays connected to the server.

Initial target:

- Raspberry Pi
- 4 x HD44780 16x2 LCD displays
- I2C backpack adapters
- One I2C bus with different addresses
- Headless operation through SSH and systemd

Protocol example:

```json
{"cmd":"display","target":"rack1","lines":["Exterior","13.7 C"]}
```
