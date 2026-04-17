---
name: logger
description: >
  Instrucciones para registrar eventos en este proyecto. Úsala siempre que vayas
  a escribir cualquier evento, traza, aviso o error en código Python del proyecto —
  da igual si el contexto es un nuevo fichero, una corrección de bug, o una adición
  de funcionalidad. No uses print(), logging ni ningún otro mecanismo de registro:
  usa exclusivamente _log de src/servidor/monitorizacion/logger.py.
---

## Regla principal

Cuando necesites registrar un evento en cualquier script Python del proyecto,
importa y usa `_log` desde `src/servidor/monitorizacion/logger.py`.

No uses `print()`, `logging.info()`, `logging.error()` ni ninguna otra forma de
registro. La única excepción es el propio `logger.py`, que internamente hace un
`print` para eco en consola — no lo imites en otros ficheros.

## Importación

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "<ruta_relativa_a_src>"))
from servidor.monitorizacion.logger import _log
```

Ajusta `<ruta_relativa_a_src>` para que apunte al directorio `src/` desde el
fichero que estás editando. Por ejemplo, desde `src/servidor/tolerancia_fallos/`:

```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from servidor.monitorizacion.logger import _log
```

## Firma de _log

```python
_log(ruta_log: str, evento: str, detalle: str) -> None
```

| Parámetro | Descripción |
|-----------|-------------|
| `ruta_log` | Ruta al fichero de log. Obtenla siempre de `config.json` (`LOG_PATH`) |
| `evento`   | Etiqueta del tipo de evento (ver tabla de eventos) |
| `detalle`  | Información específica del evento en formato `clave=valor` |

## Cómo obtener ruta_log

Lee `LOG_PATH` de `config/config.json` al inicio del módulo:

```python
import json, os

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "<ruta_relativa_a_config>", "config.json")

with open(_CONFIG_PATH) as f:
    _config = json.load(f)

LOG_PATH = _config["LOG_PATH"]
```

## Eventos definidos en el proyecto

| evento            | Cuándo usarlo                                      |
|-------------------|----------------------------------------------------|
| `CAIDA_CLIENTE`   | El servidor detecta que un cliente no responde     |
| `CAIDA_SERVIDOR`  | El cliente detecta que su servidor no responde     |
| `RECONEXION`      | Un cliente se reconecta a un nuevo servidor        |

Si necesitas un evento nuevo que no está en la tabla, añádelo aquí y en el
CLAUDE.md del proyecto con su descripción.

## Ejemplos de uso

```python
_log(LOG_PATH, "CAIDA_CLIENTE",  "client_ip=192.168.1.20")
_log(LOG_PATH, "CAIDA_SERVIDOR", "server_ip=192.168.1.10")
_log(LOG_PATH, "RECONEXION",     "client_ip=192.168.1.30 nuevo_servidor=192.168.1.11")
```

Salida generada:
```
[2026-04-17 10:23:01] [CAIDA_SERVIDOR  ] server_ip=192.168.1.10
[2026-04-17 10:23:06] [RECONEXION      ] client_ip=192.168.1.30 nuevo_servidor=192.168.1.11
[2026-04-17 10:25:00] [CAIDA_CLIENTE   ] client_ip=192.168.1.20
```
