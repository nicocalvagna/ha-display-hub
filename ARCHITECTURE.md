# Architecture

HA Display Hub is a display server.

It does not know about Home Assistant entities. Its only job is to receive display commands and render them on physical displays.

```text
Home Assistant client
        |
        | TCP + JSON
        v
HA Display Hub server
        |
        | I2C
        +-- LCD rack1 0x27
        +-- LCD rack2 0x26
        +-- LCD rack3 0x25
        +-- LCD rack4 0x24
```

The first implementation includes a mock driver so the TCP server can be tested before touching I2C.
