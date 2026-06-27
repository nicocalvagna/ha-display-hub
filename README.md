# HA Display Hub

HA Display Hub is a lightweight display server designed to work alongside Home Assistant.

Instead of driving displays directly from Home Assistant, a dedicated server manages one or more physical displays connected to a Raspberry Pi or any Linux device.

The communication protocol is simple, fast and based on TCP + JSON, allowing clients to update multiple displays simultaneously.

## Planned features

- HD44780 LCD (I²C)
- Multiple displays on the same I²C bus
- TCP/JSON protocol
- Multiple independent clients
- Screen priorities
- Widgets (text, bars, gauges, clocks, icons)
- OLED support
- VFD support
- Extensible backend architecture

The goal is to become a generic display server for Home Assistant and other automation systems.
