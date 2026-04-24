# Adminsis2 — Sistema de Monitorización Distribuida

Sistema de monitorización distribuido con tolerancia a fallos para entornos Linux.
Gestiona N servidores y N clientes de forma autónoma, sin intervención del administrador.

---

## Estructura del proyecto

```
src/
├── cliente/
│   ├── monitorizacion/
│   │   ├── __init__.py              # Inicialización del módulo de monitorización de cliente
│   │   └── cliente_monitor.py       # RU4 — Cliente monitorizado por un servidor
│   └── tolerancia_fallos/
│       ├── detector_servidor.py     # CU3 — Detecta caída del servidor y se reconecta
│       └── reconexion.py            # Lógica de reconexión a un nuevo servidor
└── servidor/
    ├── monitorizacion/
    │   ├── logger.py                # Módulo de log compartido — usar desde cualquier componente
    │   ├── metricas.py              # SRV5/SRV7/SRV8 — Recogida de métricas y cálculo de carga
    │   └── servidor_monitor.py      # SRV5/SRV7/SRV8/SRV9 — Monitorización y reasignación
    ├── logs/
    │   └── eventos.log              # Fichero de eventos (generado en tiempo de ejecución)
    └── tolerancia_fallos/
        └── monitor_clientes.py      # CU4 — Detecta caída de clientes y notifica al admin

config/
└── config.json                      # Parámetros globales del sistema
```

---

## Módulos disponibles para el equipo

### `src/servidor/monitorizacion/logger.py` — Log de eventos (TODOS)

Módulo compartido para escribir en `src/servidor/logs/eventos.log`.
**Solo el servidor escribe en el log** (SRV-6).

```python
from monitorizacion.logger import _log

_log(ruta_log, "CAIDA_CLIENTE", "client_ip=192.168.1.20")
_log(ruta_log, "CAIDA_SERVIDOR", "server_ip=192.168.1.10")
_log(ruta_log, "RECONEXION",    "client_ip=192.168.1.30")
```

Formato de salida:
```
[2026-04-16 10:23:01] [CAIDA_SERVIDOR  ] server_ip=192.168.1.10
[2026-04-16 10:23:06] [RECONEXION      ] client_ip=192.168.1.30
[2026-04-16 10:25:00] [CAIDA_CLIENTE   ] client_ip=192.168.1.20
```

La ruta del log se obtiene desde `config.json` (`LOG_PATH`).

---

## Protocolo de mensajes (acordado con Persona 2)

| Mensaje | Dirección | Descripción |
|---|---|---|
| `HEARTBEAT` | Cliente → Servidor | Comprobación de vida periódica |
| `HEARTBEAT_ACK` | Servidor → Cliente | Confirmación de que el servidor sigue activo |
| `RECONNECT_REQUEST client server_caido=<ip>` | Cliente → Nuevo Servidor | Solicitud de reconexión tras caída |
| `RECONNECT_OK` | Nuevo Servidor → Cliente | Reconexión aceptada |
| `CLIENT_DOWN` | Servidor → Admin | Notificación de caída de cliente |

---

## Configuración (`config/config.json`)

| Parámetro | Valor | Descripción |
|---|---|---|
| `HEARTBEAT_INTERVAL` | 3 | Segundos entre heartbeats |
| `HEARTBEAT_TIMEOUT` | 5 | Segundos máximos de espera de respuesta |
| `MAX_FALLOS` | 3 | Fallos consecutivos para declarar caída |
| `PUERTO_TCP` | 9000 | Puerto de comunicación entre nodos |
| `LOG_PATH` | `src/servidor/logs/eventos.log` | Ruta del fichero de eventos |

---

## Desarrollo del proyecto

Leyenda de estado: `[HECHO]` implementado y funcional · `[PARCIAL]` implementado pero con dependencias pendientes · `[PENDIENTE]` sin implementar

---

### Requisitos de Usuario (Cliente)

**RU-1 — Alta de nuevo cliente sin argumentos**
- Estado: `[PENDIENTE]`
- Responsable: Persona 1
- Descripción: —
- Pendiente: —

**RU-2 — Alta de nuevo cliente pasando IP de servidor**
- Estado: `[PENDIENTE]`
- Responsable: Persona 1
- Descripción: —
- Pendiente: —

**RU-3 — Parada de ejecución si no hay servidores**
- Estado: `[PARCIAL]`
- Responsable: Persona 3
- Descripción: `detector_servidor.py` para su ejecución cuando `intentar_reconexion()` agota todos los servidores disponibles y devuelve `None`
- Pendiente: la lista real de servidores la proveerá Persona 1 (actualmente stub)

**RU-4 — Monitorización del cliente por un servidor**
- Estado: `[HECHO]`
- Responsable: Persona 4
- Descripción: `cliente_monitor.py` permite que, una vez dado de alta el cliente en un servidor operativo, quede monitorizado por dicho servidor y mantenga el envío periódico de información de monitorización.
- Pendiente: —

**RU-5 — Envío de información de monitorización al servidor**
- Estado: `[PENDIENTE]`
- Responsable: Persona 2
- Descripción: —
- Pendiente: —

**RU-6 — Detección de caída del servidor y reconexión transparente**
- Estado: `[PARCIAL]`
- Responsable: Persona 3
- Descripción: `detector_servidor.py` cuenta fallos consecutivos de heartbeat y llama a `reconexion.py` para conectarse a otro servidor de forma transparente. Al reconectarse informa al nuevo servidor del servidor caído.
- Pendiente: integración con el canal TCP real de Persona 2 y lista de servidores de Persona 1

---

### Requisitos de Servidor

**SRV-1 — Alta de nuevo servidor sin argumentos**
- Estado: `[PENDIENTE]`
- Responsable: Persona 1
- Descripción: —
- Pendiente: —

**SRV-2 — Alta de nuevo servidor con IP de otro servidor**
- Estado: `[PENDIENTE]`
- Responsable: Persona 1
- Descripción: —
- Pendiente: —

**SRV-3 — Recepción de peticiones de alta por TCP**
- Estado: `[PENDIENTE]`
- Responsable: Persona 2
- Descripción: —
- Pendiente: —

**SRV-4 — Monitorización de los clientes asignados**
- Estado: `[PENDIENTE]`
- Responsable: Persona 2
- Descripción: —
- Pendiente: —

**SRV-5 — Monitorización de aspectos del cliente (ancho de banda, SO, CPU, memoria, almacenamiento, red)**
- Estado: `[HECHO]`
- Responsable: Persona 4
- Descripción: `metricas.py` y `servidor_monitor.py` recogen y procesan de cada cliente el ancho de banda de subida, sistema operativo e información del nodo, usuarios, CPU, memoria, almacenamiento y red.
- Pendiente: —

**SRV-6 — Almacenar eventos en fichero log**
- Estado: `[PARCIAL]`
- Responsable: Persona 3
- Descripción: `monitorizacion/logger.py` escribe en `src/servidor/logs/eventos.log` con formato acordado. Registra `CAIDA_CLIENTE`, `CAIDA_SERVIDOR` y `RECONEXION`. Solo el servidor escribe en el log.
- Pendiente: Persona 4 puede ampliar con más tipos de evento usando el mismo módulo

**SRV-7 — Almacenar datos monitorizados en fichero log**
- Estado: `[HECHO]`
- Responsable: Persona 4
- Descripción: `servidor_monitor.py` almacena en `src/servidor/logs/datos_monitorizados.log` los datos monitorizados recibidos de sus clientes.
- Pendiente: —

**SRV-8 — Carga del servidor por tiempo de monitorización y hardware**
- Estado: `[HECHO]`
- Responsable: Persona 4
- Descripción: `metricas.py` calcula la carga del servidor a partir del tiempo medio de monitorización, el número de clientes activos y la información hardware disponible, guardándola en ficheros `carga_srv*.json`.
- Pendiente: —

**SRV-9 — Reasignación de cliente a servidor con menor carga**
- Estado: `[HECHO]`
- Responsable: Persona 4
- Descripción: `servidor_monitor.py` compara la carga local con la de otros servidores conocidos y solicita la reasignación del cliente a otro servidor cuando detecta menor carga.
- Pendiente: —

**SRV-10 — Notificación al administrador ante caída de cliente**
- Estado: `[PARCIAL]`
- Responsable: Persona 3
- Descripción: `monitor_clientes.py` llama a `notificar_admin(ip)` cuando el watchdog detecta que un cliente ha dejado de enviar heartbeats
- Pendiente: implementación real del canal de notificación por Persona 2 (actualmente stub)

---
