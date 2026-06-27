# Protocol

HA Display Hub uses TCP with newline-delimited JSON.

Default port: `4510`

## ping

```json
{"cmd":"ping"}
```

Response:

```json
{"status":"ok","message":"pong"}
```

## info

```json
{"cmd":"info"}
```

Response:

```json
{"status":"ok","version":"0.1.0","displays":["rack1","rack2"]}
```

## clear

```json
{"cmd":"clear","target":"rack1"}
```

## display

```json
{"cmd":"display","target":"rack1","lines":["Exterior","13.7 C"]}
```
