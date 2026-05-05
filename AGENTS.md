# CLAUDE.md — Proyecto Administración de Sistemas 2

## Descripción del Proyecto

Sistema de monitorización distribuido con tolerancia a fallos para entornos heterogéneos Linux.
El sistema gestiona **N servidores** y **N clientes** de forma autónoma, sin intervención del
administrador, y se adapta automáticamente ante caídas de nodos.

---

## Tecnologías

- **SO**: Linux (Ubuntu/Debian) en todas las máquinas
- **Monitorización**: Zabbix con stack LAMP (Apache, MySQL, PHP)
- **Scripts**: Python 3.8+
- **Protocolo de comunicación**: TCP
- **Control de versiones**: Git (GitHub/GitLab)

---

## Arquitectura General

El sistema tiene dos tipos de nodos:

- **Servidor**: monitoriza a los clientes asignados, gestiona su estado y balancea carga.
- **Cliente**: nodo monitorizado, capaz de unirse al sistema de forma autónoma y adaptarse ante caídas.

Zabbix actúa como motor de monitorización. Los scripts Python son la capa de automatización
y tolerancia a fallos que Zabbix no cubre por defecto.

---

## Estructura del Proyecto

```
src/
├── cliente/
│   └── tolerancia_fallos/
│       ├── detector_servidor.py     # CU3 — Detecta caída del servidor y se reconecta
│       └── reconexion.py            # Lógica de reconexión a un nuevo servidor
└── servidor/
    ├── monitorizacion/
    │   └── logger.py                # Módulo de log compartido — usar desde cualquier componente
    ├── logs/
    │   └── eventos.log              # Fichero de eventos (generado en tiempo de ejecución)
    └── tolerancia_fallos/
        └── monitor_clientes.py      # CU4 — Detecta caída de clientes y notifica al admin

config/
└── config.json                      # Parámetros globales del sistema
```

---

## Distribución de Responsabilidades

| Persona | Área |
|---|---|
| Persona 1 | Alta e incorporación de nodos (CU1, CU2) |
| Persona 2 | Comunicación TCP y monitorización (RS-3, RS-4, RS-5) |
| Persona 3 | Tolerancia a fallos (CU3, CU4) |
| Persona 4 | Logs y métricas (RS-6, RS-7, RS-8, RS-9) |

---

## Casos de Uso

**CU1 — Inserción de un nuevo Servidor**

| Campo | Descripción |
|---|---|
| **Designación** | Inserción de un nuevo Servidor |
| **Objetivo** | Insertar un nuevo nodo al sistema |
| **Precondiciones** | Ninguna |
| **Postcondiciones** | Sistema con un nuevo servidor en estado de monitorización |
| **Operaciones** | 1. El sujeto ejecuta los scripts correspondientes al nuevo caso de uso "servidor" |
| | 2. El servidor se une al sistema de manera automática y autónoma y comienza a monitorizar a los clientes |

---

**CU2 — Inserción de un nuevo Cliente**

| Campo | Descripción |
|---|---|
| **Designación** | Inserción de un nuevo Cliente |
| **Objetivo** | Insertar un nuevo nodo al sistema |
| **Precondiciones** | Ninguna |
| **Postcondiciones** | Sistema con un nuevo cliente siendo monitorizado por un servidor del sistema |
| **Operaciones** | 1. El sujeto ejecuta los scripts correspondientes al nuevo caso de uso "cliente" |
| | 2. El cliente se une al sistema de manera automática y autónoma y está monitorizado por un servidor del sistema |

---

**CU3 — Caída de un nodo Servidor**

| Campo | Descripción |
|---|---|
| **Designación** | Caída de un nodo Servidor |
| **Objetivo** | Detección de la caída de un nodo servidor para volver a adaptarse al sistema |
| **Precondiciones** | El nodo servidor se encontrará en ejecución monitorizando a los clientes. Sistema se encontrará en funcionamiento sin errores. |
| **Postcondiciones** | El cliente vuelve a ser monitorizado por algún servidor |
| **Operaciones** | 1. El cliente detecta la caída del servidor |
| | 2. El cliente lleva a cabo las correspondientes acciones para volver a adaptarse al sistema y volver a ser monitorizado por algún servidor |

---

**CU4 — Caída de un nodo Cliente**

| Campo | Descripción |
|---|---|
| **Designación** | Caída de un nodo Cliente |
| **Objetivo** | Detección de la caída de un nodo cliente para volver a adaptarse el sistema a un estado estable |
| **Precondiciones** | El nodo cliente se encontrará en ejecución y monitorizado por un servidor del sistema. Sistema en correcto funcionamiento sin errores. |
| **Postcondiciones** | El sistema se encuentra en un estado estable |
| **Operaciones** | 1. El servidor detecta la caída del cliente |
| | 2. El servidor lleva a cabo las correspondientes acciones para que el sistema se encuentre en un estado estable |

---

**CU5 — Monitorización de Clientes**

| Campo | Descripción |
|---|---|
| **Designación** | Monitorización de Clientes |
| **Objetivo** | Monitorizar a los clientes que se encuentran en ejecución |
| **Precondiciones** | Existencia mínima de un servidor en ejecución |
| **Postcondiciones** | Captura de la información de los clientes por parte del servidor y su posterior almacenamiento |
| **Operaciones** | 1. El servidor captura la información de los clientes |
| | 2. El servidor visualiza la información obtenida y la guarda en algún dispositivo de almacenamiento |

---

## Requisitos de Usuario

**RU-1 — Alta de nuevo cliente sin argumentos**

| Campo | Descripción |
|---|---|
| **Designación** | Alta de nuevo cliente sin argumentos |
| **Objetivo** | Dar de alta a un nuevo usuario sin el paso de ningún tipo de argumentos |
| **Precondiciones** | Ninguna |
| **Postcondiciones** | El alta se realizará de forma automática y transparente una vez ejecutados los scripts correspondientes sin el paso de ningún argumento |

---

**RU-2 — Alta de nuevo cliente pasando la IP de un servidor**

| Campo | Descripción |
|---|---|
| **Designación** | Alta de nuevo cliente pasando la IP de un servidor |
| **Objetivo** | Dar de alta a un nuevo usuario con el paso de la dirección IP de un servidor del sistema |
| **Precondiciones** | Ninguna |
| **Postcondiciones** | El cliente se unirá al sistema automáticamente una vez ejecutados los scripts pasándole como argumento la dirección IP de un servidor en ejecución |

---

**RU-3 — Fin de la ejecución del cliente**

| Campo | Descripción |
|---|---|
| **Designación** | Fin de la ejecución del cliente |
| **Objetivo** | Finalización de la ejecución por parte del cliente si no existe ningún servidor en ejecución |
| **Precondiciones** | Ninguna |
| **Postcondiciones** | El cliente finalizará su ejecución en el caso de no existir ningún servidor en el sistema en ejecución |

---

**RU-4 — Monitorización del cliente**

| Campo | Descripción |
|---|---|
| **Designación** | Monitorización del cliente |
| **Objetivo** | Monitorización del cliente por parte de uno de los servidores en ejecución |
| **Precondiciones** | Cliente dado de alta |
| **Postcondiciones** | El cliente será monitorizado por alguno de los servidores del sistema |

---

**RU-5 — Información de monitorización del cliente al servidor**

| Campo | Descripción |
|---|---|
| **Designación** | Información de monitorización del cliente al servidor |
| **Objetivo** | Envío de datos de monitorización del cliente al servidor |
| **Precondiciones** | Tras dar de alta al cliente en el sistema |
| **Postcondiciones** | El servidor deberá mandar una petición al cliente para que pueda ser monitorizado |

---

**RU-6 — Detección de caída del servidor**

| Campo | Descripción |
|---|---|
| **Designación** | Detección de caída del servidor |
| **Objetivo** | Adaptación del cliente a un nuevo servidor en ejecución |
| **Precondiciones** | Tras la caída de un servidor |
| **Postcondiciones** | El cliente deberá ser capaz de adaptarse para comenzar a ser monitorizado por otro servidor de forma transparente |

---

## Requisitos de Servidor

**RS-1 — Alta de nuevo servidor sin argumentos**

| Campo | Descripción |
|---|---|
| **Designación** | Alta de nuevo servidor sin argumentos |
| **Objetivo** | Dar de alta a un nuevo servidor sin el paso de ningún tipo de argumentos |
| **Precondiciones** | Ninguna |
| **Postcondiciones** | El alta se realizará de forma automática y transparente una vez ejecutados los scripts sin el paso de ningún argumento |

---

**RS-2 — Alta de nuevo servidor con la dirección IP de un servidor**

| Campo | Descripción |
|---|---|
| **Designación** | Alta de nuevo servidor con la dirección IP de un servidor |
| **Objetivo** | Dar de alta a un nuevo servidor con el paso de la dirección IP de un servidor del sistema |
| **Precondiciones** | Ninguna |
| **Postcondiciones** | El servidor se unirá automáticamente al sistema tras ejecutar los scripts con la dirección IP de un servidor en ejecución |

---

**RS-3 — Recepción de peticiones por TCP**

| Campo | Descripción |
|---|---|
| **Designación** | Recepción de peticiones por TCP |
| **Objetivo** | Uso del protocolo TCP para la recepción de peticiones de altas |
| **Precondiciones** | Ninguna |
| **Postcondiciones** | El servidor recibirá peticiones de alta en el sistema gracias al protocolo TCP |

---

**RS-4 — Monitorización**

| Campo | Descripción |
|---|---|
| **Designación** | Monitorización |
| **Objetivo** | Monitorización de los clientes asignados al servidor |
| **Precondiciones** | Asignación previa de clientes |
| **Postcondiciones** | El servidor monitorizará a los clientes previamente asignados |

---

**RS-5 — Información de Monitorización**

| Campo | Descripción |
|---|---|
| **Designación** | Información de Monitorización |
| **Objetivo** | Monitorización de un conjunto de aspectos relevantes de cada uno de los clientes |
| **Precondiciones** | Clientes asignados al servidor |
| **Postcondiciones** | El servidor monitorizará: Ancho de banda (subida), SO e información del nodo, Usuarios, CPU, Memoria, Almacenamiento y Tarjeta de red |

---

**RS-6 — Generación de un log de eventos**

| Campo | Descripción |
|---|---|
| **Designación** | Generación de un log de eventos |
| **Objetivo** | Almacenamiento de los eventos producidos en el sistema |
| **Precondiciones** | Producción de eventos en el sistema |
| **Postcondiciones** | El servidor almacenará en un fichero log los eventos que se van produciendo referentes al sistema |

---

**RS-7 — Generación de un log de los datos monitorizados**

| Campo | Descripción |
|---|---|
| **Designación** | Generación de un log de los datos monitorizados |
| **Objetivo** | Almacenamiento de los datos monitorizados en el sistema |
| **Precondiciones** | Captura de información de monitorización |
| **Postcondiciones** | El servidor almacenará en un fichero log los eventos referentes a la información que monitoriza de sus clientes |

---

**RS-8 — Carga del servidor**

| Campo | Descripción |
|---|---|
| **Designación** | Carga del servidor |
| **Objetivo** | Obtención de la carga del Servidor |
| **Precondiciones** | Ninguna |
| **Postcondiciones** | La carga será establecida por el tiempo de monitorización y los recursos hardware disponibles |

---

**RS-9 — Reasignación cliente-servidor**

| Campo | Descripción |
|---|---|
| **Designación** | Reasignación cliente-servidor |
| **Objetivo** | Reasignación cliente-servidor en función de la carga |
| **Precondiciones** | Que el servidor actual tenga mayor carga |
| **Postcondiciones** | El cliente será reasignado a otro servidor |

---

**RS-10 — Caída del Cliente**

| Campo | Descripción |
|---|---|
| **Designación** | Caída del Cliente |
| **Objetivo** | Información al administrador de la caída de un cliente |
| **Precondiciones** | Caída de un cliente monitorizado por un servidor |
| **Postcondiciones** | El administrador recibirá información sobre la caída de dicho cliente |

---

## Requisitos de Restricción

**RES-1 — Número de Servidores y Clientes**

| Campo | Descripción |
|---|---|
| **Designación** | Número de Servidores y Clientes |
| **Objetivo** | Sistema totalmente operativo con N Servidores y N clientes |
| **Precondiciones** | Ninguna |
| **Postcondiciones** | El sistema será funcional con cualquier número de servidores y clientes |

---

**RES-2 — SOP en el sistema**

| Campo | Descripción |
|---|---|
| **Designación** | SOP en el sistema |
| **Objetivo** | SOP Linux en el Sistema |
| **Precondiciones** | Ninguna |
| **Postcondiciones** | El Sistema funcionará teniendo en todas las máquinas el sistema operativo Linux |

---

## Protocolo de Mensajes TCP

| Mensaje | Dirección | Descripción |
|---|---|---|
| `HEARTBEAT` | Cliente → Servidor | Comprobación de vida periódica |
| `HEARTBEAT_ACK` | Servidor → Cliente | Confirmación de que el servidor sigue activo |
| `RECONNECT_REQUEST client server_caido=<ip>` | Cliente → Nuevo Servidor | Solicitud de reconexión tras caída |
| `RECONNECT_OK` | Nuevo Servidor → Cliente | Reconexión aceptada |
| `CLIENT_DOWN` | Servidor → Admin | Notificación de caída de cliente |

---

## Configuración Global (`config/config.json`)

| Parámetro | Valor | Descripción |
|---|---|---|
| `HEARTBEAT_INTERVAL` | 3 | Segundos entre heartbeats |
| `HEARTBEAT_TIMEOUT` | 5 | Segundos máximos de espera de respuesta |
| `MAX_FALLOS` | 3 | Fallos consecutivos para declarar caída |
| `PUERTO_TCP` | 9000 | Puerto de comunicación entre nodos |
| `LOG_PATH` | `src/servidor/logs/eventos.log` | Ruta del fichero de eventos |

---

## Módulo de Log Compartido (`src/servidor/monitorizacion/logger.py`)

Módulo compartido para escribir en `src/servidor/logs/eventos.log`.
**Solo el servidor escribe en el log** (RS-6).

```python
from monitorizacion.logger import _log

_log(ruta_log, "CAIDA_CLIENTE",  "client_ip=192.168.1.20")
_log(ruta_log, "CAIDA_SERVIDOR", "server_ip=192.168.1.10")
_log(ruta_log, "RECONEXION",     "client_ip=192.168.1.30")
```

Formato de salida:
```
[2026-04-16 10:23:01] [CAIDA_SERVIDOR  ] server_ip=192.168.1.10
[2026-04-16 10:23:06] [RECONEXION      ] client_ip=192.168.1.30
[2026-04-16 10:25:00] [CAIDA_CLIENTE   ] client_ip=192.168.1.20
```

La ruta del log se obtiene desde `config.json` (`LOG_PATH`).