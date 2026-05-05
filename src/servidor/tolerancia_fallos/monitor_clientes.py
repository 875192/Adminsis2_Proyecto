"""
Monitor de clientes — CU4 (Persona 3: Tolerancia a Fallos)

Lógica del watchdog del servidor:
  - Comprueba periódicamente el campo last_seen de cada cliente registrado.
  - Si un cliente supera MAX_FALLOS * HEARTBEAT_INTERVAL segundos sin señal,
    declara su caída, registra el evento en logs/eventos.log (RS-6) y
    notifica al administrador (RS-10).

Este módulo no abre ningún socket TCP propio; se integra con servidor_monitor.py
que ya escucha en el puerto 9000 y actualiza estado.clientes en cada HEARTBEAT
o METRICS recibido.

Uso (integrado en servidor_monitor.py):
    from tolerancia_fallos.monitor_clientes import iniciar_watchdog
    activo = iniciar_watchdog(estado, ruta_log, config)
    # Al cerrar el servidor:
    activo.clear()
"""

import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from monitorizacion.logger import _log
from tolerancia_fallos.notificacion_admin import notificar_admin


# ---------------------------------------------------------------------------
# Watchdog
# ---------------------------------------------------------------------------

def _watchdog(
    estado,
    umbral: float,
    ruta_log: str,
    activo: threading.Event,
    intervalo: float,
    admin_host: str,
    admin_puerto: int,
) -> None:
    """
    Hilo daemon que comprueba periódicamente si algún cliente ha dejado de
    enviar señales (HEARTBEAT o METRICS). Opera sobre estado.clientes de
    EstadoMonitor (servidor_monitor.py).
    """
    while activo.is_set():
        time.sleep(intervalo)
        ahora = time.time()

        with estado.lock:
            caidos = [
                (client_id, datos["client_ip"])
                for client_id, datos in list(estado.clientes.items())
                if ahora - datos["last_seen"] > umbral
            ]

        for client_id, client_ip in caidos:
            _log(ruta_log, "CAIDA_CLIENTE", f"client_ip={client_ip}")
            notificar_admin(client_ip, admin_host, admin_puerto)
            with estado.lock:
                estado.clientes.pop(client_id, None)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def iniciar_watchdog(estado, ruta_log: str, config: dict) -> threading.Event:
    """
    Arranca el hilo watchdog y devuelve el evento de control.

    Parámetros
    ----------
    estado : EstadoMonitor
        Estado compartido del servidor (de servidor_monitor.py).
    ruta_log : str
        Ruta absoluta al fichero logs/eventos.log.
    config : dict
        Configuración global del sistema (config.json).

    Retorna
    -------
    threading.Event
        Evento activo mientras el watchdog está en marcha.
        Llama a activo.clear() para detenerlo.
    """
    intervalo: float  = config["HEARTBEAT_INTERVAL"]
    max_fallos: int   = config["MAX_FALLOS"]
    umbral: float     = max_fallos * intervalo
    admin_host: str   = config.get("ADMIN_HOST", "")
    admin_puerto: int = int(config.get("ADMIN_PUERTO", 9099))

    activo = threading.Event()
    activo.set()

    hilo = threading.Thread(
        target=_watchdog,
        args=(estado, umbral, ruta_log, activo, intervalo, admin_host, admin_puerto),
        daemon=True,
    )
    hilo.start()
    return activo
