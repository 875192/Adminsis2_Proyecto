"""
Monitor de clientes — CU4 (Persona 3: Tolerancia a Fallos)

Lógica principal del servidor:
  - Escucha HEARTBEATs entrantes de los clientes asignados.
  - Lleva un registro del último heartbeat recibido por cada cliente.
  - Un hilo watchdog comprueba periódicamente si algún cliente ha
    superado el umbral MAX_FALLOS * HEARTBEAT_INTERVAL sin dar señal.
  - Si un cliente supera el umbral: declara su caída, registra el evento
    en logs/eventos.log y notifica al administrador (SRV-10).

Uso:
    python monitor_clientes.py <ip1> [<ip2> ...] [--modo-fallo <ip>]

    --modo-fallo <ip>   Simula que ese cliente deja de enviar heartbeats
                        tras MAX_FALLOS mensajes (para probar CU4).
"""

import argparse
import json
import os
import threading
import time
from datetime import datetime

from stubs.tcp_escucha import EscuchaTCP
from stubs.notificacion_admin import notificar_admin


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

def _cargar_config() -> dict:
    ruta = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "config", "config.json"
    )
    with open(os.path.normpath(ruta), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _log(ruta_log: str, evento: str, detalle: str) -> None:
    """Escribe una línea en logs/eventos.log con el formato acordado."""
    marca = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{marca}] [{evento:<16}] {detalle}\n"

    os.makedirs(os.path.dirname(ruta_log), exist_ok=True)
    with open(ruta_log, "a", encoding="utf-8") as f:
        f.write(linea)

    print(linea, end="")


# ---------------------------------------------------------------------------
# Watchdog
# ---------------------------------------------------------------------------

def _watchdog(
    ultimo_heartbeat: dict[str, float],
    lock: threading.Lock,
    umbral: float,
    ruta_log: str,
    activo: threading.Event,
    intervalo: float,
) -> None:
    """
    Hilo que comprueba periódicamente si algún cliente ha dejado de
    enviar heartbeats. Se ejecuta en segundo plano.
    """
    while activo.is_set():
        time.sleep(intervalo)
        ahora = time.monotonic()

        with lock:
            caidos = [
                ip
                for ip, ts in list(ultimo_heartbeat.items())
                if ahora - ts > umbral
            ]

        for ip in caidos:
            _log(ruta_log, "CAIDA_CLIENTE", f"client_ip={ip}")
            notificar_admin(ip)
            with lock:
                ultimo_heartbeat.pop(ip, None)


# ---------------------------------------------------------------------------
# Bucle principal
# ---------------------------------------------------------------------------

def ejecutar(clientes: list[str], ip_fallo: str | None = None) -> None:
    config = _cargar_config()

    intervalo: float = config["HEARTBEAT_INTERVAL"]
    timeout: float   = config["HEARTBEAT_TIMEOUT"]
    max_fallos: int  = config["MAX_FALLOS"]
    ruta_log: str    = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", config["LOG_PATH"])
    )

    umbral = max_fallos * intervalo

    modo_fallo = {ip_fallo: max_fallos} if ip_fallo else {}
    escucha = EscuchaTCP(
        clientes=clientes,
        intervalo=intervalo,
        modo_fallo=modo_fallo,
    )

    # Inicializa timestamps con el momento actual
    lock = threading.Lock()
    ultimo_heartbeat: dict[str, float] = {ip: time.monotonic() for ip in clientes}

    activo = threading.Event()
    activo.set()

    hilo_watchdog = threading.Thread(
        target=_watchdog,
        args=(ultimo_heartbeat, lock, umbral, ruta_log, activo, intervalo),
        daemon=True,
    )
    hilo_watchdog.start()

    print(f"[INFO] Servidor iniciado. Monitorizando: {', '.join(clientes)}")

    try:
        while True:
            resultado = escucha.siguiente_heartbeat(timeout=timeout)

            if resultado is not None:
                ip_cliente, mensaje = resultado
                if mensaje == "HEARTBEAT":
                    with lock:
                        if ip_cliente in ultimo_heartbeat:
                            ultimo_heartbeat[ip_cliente] = time.monotonic()

            # Si no quedan clientes activos, no hay nada que monitorizar
            with lock:
                if not ultimo_heartbeat:
                    print("[INFO] No quedan clientes activos. Cerrando monitor.")
                    break

    except KeyboardInterrupt:
        print("\n[INFO] Monitor detenido manualmente.")
    finally:
        activo.clear()
        escucha.cerrar()


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor de clientes (CU4)")
    parser.add_argument(
        "clientes",
        nargs="+",
        help="IPs de los clientes a monitorizar",
    )
    parser.add_argument(
        "--modo-fallo",
        metavar="IP",
        default=None,
        help="IP del cliente que simulará una caída (para probar CU4)",
    )
    args = parser.parse_args()

    ejecutar(clientes=args.clientes, ip_fallo=args.modo_fallo)
