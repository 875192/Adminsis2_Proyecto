---
name: tcp-protocol
description: >
  Protocolo TCP de este proyecto. Úsala siempre que vayas a escribir, modificar
  o revisar código Python que envíe o reciba mensajes entre nodos (cliente-servidor,
  servidor-servidor, servidor-admin). Garantiza que los mensajes, puerto y flujos
  de comunicación sean exactamente los definidos para el proyecto — no inventes
  mensajes nuevos ni uses puertos distintos.
---

## Puerto

Todos los nodos escuchan y se conectan en el puerto definido en `config.json`:

```python
import json, os

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "<ruta_relativa_a_config>", "config.json")
with open(_CONFIG_PATH) as f:
    _config = json.load(f)

PUERTO_TCP = _config["PUERTO_TCP"]  # 9000
```

## Mensajes definidos

| Mensaje | Dirección | Descripción |
|---------|-----------|-------------|
| `HEARTBEAT` | Cliente → Servidor | Comprobación de vida periódica |
| `HEARTBEAT_ACK` | Servidor → Cliente | Confirmación de que el servidor sigue activo |
| `RECONNECT_REQUEST client=<ip> server_caido=<ip>` | Cliente → Nuevo Servidor | Solicitud de reconexión tras caída |
| `RECONNECT_OK` | Nuevo Servidor → Cliente | Reconexión aceptada |
| `CLIENT_DOWN` | Servidor → Admin | Notificación de caída de cliente |

No uses ningún otro mensaje. Si necesitas uno nuevo, añádelo aquí y en el CLAUDE.md del proyecto.

## Parámetros de temporización

Léelos siempre de `config.json`, nunca los hardcodees:

| Parámetro | Valor | Uso |
|-----------|-------|-----|
| `HEARTBEAT_INTERVAL` | 3 s | Segundos entre envíos de `HEARTBEAT` |
| `HEARTBEAT_TIMEOUT` | 5 s | Tiempo máximo de espera de respuesta |
| `MAX_FALLOS` | 3 | Fallos consecutivos para declarar caída |

## Patrón de envío/recepción

```python
import socket

def enviar_mensaje(ip: str, puerto: int, mensaje: str) -> str | None:
    try:
        with socket.create_connection((ip, puerto), timeout=HEARTBEAT_TIMEOUT) as s:
            s.sendall((mensaje + "\n").encode())
            return s.recv(1024).decode().strip()
    except (ConnectionRefusedError, TimeoutError, OSError):
        return None
```

- Termina cada mensaje con `\n`
- Usa `timeout=HEARTBEAT_TIMEOUT` en todas las conexiones
- Devuelve `None` ante cualquier fallo de red — el llamador decide si es un fallo

## Flujo heartbeat (cliente)

```
cada HEARTBEAT_INTERVAL segundos:
    respuesta = enviar_mensaje(servidor_ip, PUERTO_TCP, "HEARTBEAT")
    si respuesta != "HEARTBEAT_ACK":
        incrementar contador de fallos
        si fallos >= MAX_FALLOS:
            iniciar reconexión  ← ver skill tolerancia-fallos
    si no:
        resetear contador de fallos
```

## Flujo reconexión (cliente → nuevo servidor)

```
mensaje = f"RECONNECT_REQUEST client={mi_ip} server_caido={servidor_caido_ip}"
respuesta = enviar_mensaje(nuevo_servidor_ip, PUERTO_TCP, mensaje)
si respuesta == "RECONNECT_OK":
    actualizar servidor activo
```
