"""
Cliente de monitorización — CU2, RC1-RC6, RU-4, RU-5 (Persona 4)

Lógica principal del cliente:
  - Se registra en un servidor en ejecución.
  - Captura métricas locales del nodo Linux.
  - Envía periódicamente dichas métricas al servidor asignado.
  - Si el servidor responde con una reasignación, cambia al nuevo servidor.
  - Hilo de heartbeat detecta la caída del servidor (CU3 / RC6) y ejecuta
    reconexión automática; termina el proceso si no quedan servidores (RC3).

Uso:
    python cliente_monitor.py                       # RC1: autodescubre servidor
    python cliente_monitor.py <ip_servidor>         # RC2: IP explícita
    python cliente_monitor.py <ip_servidor> --servidores 10.0.0.2:9000 10.0.0.3:9000
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import platform
import pwd
import shutil
import socket
import sys
import threading
import time
from typing import Any


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

def _cargar_config() -> dict[str, Any]:
    ruta = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "config", "config.json"
    )
    with open(os.path.normpath(ruta), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Autodescubrimiento de servidor (RC1)
# ---------------------------------------------------------------------------

def _descubrir_servidor(puerto: int, timeout: float = 0.3) -> str | None:
    """Busca un servidor activo en la red local probando el puerto TCP.

    Primero intenta localhost; si falla, escanea la subred /24 en paralelo
    con hasta 50 hilos y timeout corto para no tardar más de ~2 segundos.
    """
    try:
        with socket.create_connection(("127.0.0.1", puerto), timeout=timeout):
            return "127.0.0.1"
    except OSError:
        pass

    try:
        mi_ip = socket.gethostbyname(socket.gethostname())
    except OSError:
        return None

    partes = mi_ip.split(".")
    if len(partes) != 4:
        return None
    prefijo = ".".join(partes[:3])

    def _probar(i: int) -> str | None:
        ip = f"{prefijo}.{i}"
        if ip == mi_ip:
            return None
        try:
            with socket.create_connection((ip, puerto), timeout=timeout):
                return ip
        except OSError:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as pool:
        futuros = {pool.submit(_probar, i): i for i in range(1, 255)}
        for futuro in concurrent.futures.as_completed(futuros):
            resultado = futuro.result()
            if resultado is not None:
                return resultado

    return None


# ---------------------------------------------------------------------------
# Métricas locales
# ---------------------------------------------------------------------------

def _leer_texto(ruta: str) -> str:
    try:
        with open(ruta, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def _interfaces_validas() -> list[str]:
    base = "/sys/class/net"
    if not os.path.isdir(base):
        return []

    interfaces = []
    for nombre in os.listdir(base):
        if nombre == "lo":
            continue
        if os.path.isdir(os.path.join(base, nombre)):
            interfaces.append(nombre)
    return sorted(interfaces)


def _tx_bytes_total() -> int:
    total = 0
    for interfaz in _interfaces_validas():
        ruta = f"/sys/class/net/{interfaz}/statistics/tx_bytes"
        try:
            total += int(_leer_texto(ruta) or "0")
        except ValueError:
            pass
    return total


def _usuarios_sistema() -> list[str]:
    usuarios = []
    for entrada in pwd.getpwall():
        if entrada.pw_uid >= 1000 and "nologin" not in entrada.pw_shell:
            usuarios.append(entrada.pw_name)
    return sorted(set(usuarios))


def _leer_meminfo() -> dict[str, int]:
    datos: dict[str, int] = {}
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            for linea in f:
                partes = linea.replace(":", "").split()
                if len(partes) >= 2:
                    datos[partes[0]] = int(partes[1])
    except OSError:
        pass
    return datos


def _almacenamiento() -> dict[str, Any]:
    uso = shutil.disk_usage("/")
    dispositivos = []
    if os.path.isdir("/sys/block"):
        for nombre in sorted(os.listdir("/sys/block")):
            dispositivos.append(nombre)

    return {
        "raiz_total_bytes": uso.total,
        "raiz_usado_bytes": uso.used,
        "raiz_libre_bytes": uso.free,
        "dispositivos": dispositivos,
    }


def _tarjetas_red() -> list[dict[str, str]]:
    tarjetas = []
    for interfaz in _interfaces_validas():
        tarjetas.append(
            {
                "nombre": interfaz,
                "mac": _leer_texto(f"/sys/class/net/{interfaz}/address") or "desconocida",
                "estado": _leer_texto(f"/sys/class/net/{interfaz}/operstate") or "unknown",
            }
        )
    return tarjetas


def _leer_cpu_snapshot() -> tuple[int, int]:
    try:
        with open("/proc/stat", encoding="utf-8") as f:
            linea = f.readline().split()
    except OSError:
        return (0, 0)

    if not linea or linea[0] != "cpu":
        return (0, 0)

    valores = [int(x) for x in linea[1:]]
    idle = valores[3] + (valores[4] if len(valores) > 4 else 0)
    total = sum(valores)
    return idle, total


def _calcular_cpu_pct(anterior: tuple[int, int], actual: tuple[int, int]) -> float:
    idle_ant, total_ant = anterior
    idle_act, total_act = actual

    delta_idle = idle_act - idle_ant
    delta_total = total_act - total_ant

    if delta_total <= 0:
        return 0.0

    uso = 100.0 * (1.0 - (delta_idle / delta_total))
    return round(max(0.0, min(100.0, uso)), 2)


def _carga_media() -> dict[str, float]:
    try:
        uno, cinco, quince = os.getloadavg()
        return {
            "loadavg_1": round(uno, 2),
            "loadavg_5": round(cinco, 2),
            "loadavg_15": round(quince, 2),
        }
    except OSError:
        return {
            "loadavg_1": 0.0,
            "loadavg_5": 0.0,
            "loadavg_15": 0.0,
        }


def capturar_metricas(
    id_cliente: str,
    cpu_anterior: tuple[int, int],
    tx_anterior: int,
    instante_anterior: float,
) -> tuple[dict[str, Any], tuple[int, int], int, float]:
    ahora = time.time()
    actual_cpu = _leer_cpu_snapshot()
    actual_tx = _tx_bytes_total()
    meminfo = _leer_meminfo()

    mem_total_kb = meminfo.get("MemTotal", 0)
    mem_disp_kb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
    mem_usada_kb = max(0, mem_total_kb - mem_disp_kb)
    mem_pct = round((mem_usada_kb / mem_total_kb) * 100, 2) if mem_total_kb else 0.0

    intervalo = max(1e-6, ahora - instante_anterior)
    subida_bps = round((actual_tx - tx_anterior) / intervalo, 2)

    metricas = {
        "type": "METRICS",
        "client_id": id_cliente,
        "client_ip": socket.gethostbyname(socket.gethostname()) if socket.gethostname() else "127.0.0.1",
        "timestamp": round(ahora, 3),
        "bandwidth_upload_Bps": max(0.0, subida_bps),
        "system": {
            "hostname": platform.node(),
            "os": platform.system(),
            "os_version": platform.version(),
            "platform": platform.platform(),
            "kernel": platform.release(),
            "arquitectura": platform.machine(),
        },
        "users": _usuarios_sistema(),
        "cpu": {
            "cores": os.cpu_count() or 1,
            "usage_pct": _calcular_cpu_pct(cpu_anterior, actual_cpu),
            **_carga_media(),
        },
        "memory": {
            "total_kb": mem_total_kb,
            "used_kb": mem_usada_kb,
            "available_kb": mem_disp_kb,
            "usage_pct": mem_pct,
        },
        "storage": _almacenamiento(),
        "network": {
            "interfaces": _tarjetas_red(),
        },
    }

    return metricas, actual_cpu, actual_tx, ahora


# ---------------------------------------------------------------------------
# Comunicación
# ---------------------------------------------------------------------------

def _enviar_mensaje(ip: str, puerto: int, payload: dict[str, Any]) -> str | None:
    mensaje = (json.dumps(payload) + "\n").encode("utf-8")

    try:
        with socket.create_connection((ip, puerto), timeout=5) as sock:
            sock.sendall(mensaje)
            sock.shutdown(socket.SHUT_WR)
            respuesta = sock.recv(4096)
    except OSError:
        return None

    if not respuesta:
        return None
    return respuesta.decode("utf-8").strip()


def _registrar_cliente(
    ip: str, puerto: int, id_cliente: str, servidores: list[str], intervalo_default: float = 5.0
) -> float | None:
    """Registra el cliente en el servidor y devuelve el intervalo de monitorización
    indicado por el servidor en su MONITOR_REQUEST (RU-5).
    Devuelve None si el servidor no responde."""
    payload = {
        "type": "REGISTER",
        "client_id": id_cliente,
        "client_ip": socket.gethostbyname(socket.gethostname()) if socket.gethostname() else "127.0.0.1",
        "known_servers": servidores,
    }
    respuesta = _enviar_mensaje(ip, puerto, payload)
    if respuesta is None:
        return None
    if respuesta.startswith("MONITOR_REQUEST"):
        try:
            return float(respuesta.split()[1])
        except (IndexError, ValueError):
            pass
    return intervalo_default


def _parsear_destino(texto: str) -> tuple[str, int] | None:
    partes = texto.split()
    if len(partes) != 3 or partes[0] != "REASSIGN":
        return None

    ip = partes[1]
    try:
        puerto = int(partes[2])
    except ValueError:
        return None
    return ip, puerto


# ---------------------------------------------------------------------------
# Tolerancia a fallos: heartbeat + reconexión (CU3 / RC6)
# ---------------------------------------------------------------------------

def _intentar_reconexion(
    servidor_caido: tuple[str, int],
    servidores: list[tuple[str, int]],
    timeout: float,
) -> tuple[str, int] | None:
    """Intenta conectar a un servidor alternativo tras detectar la caída del actual."""
    candidatos = [s for s in servidores if s != servidor_caido]
    for ip, puerto in candidatos:
        try:
            with socket.create_connection((ip, puerto), timeout=timeout) as s:
                msg = f"RECONNECT_REQUEST client server_caido={servidor_caido[0]}\n"
                s.sendall(msg.encode("utf-8"))
                s.shutdown(socket.SHUT_WR)
                if s.recv(1024).decode("utf-8").strip() == "RECONNECT_OK":
                    return (ip, puerto)
        except OSError:
            continue
    return None


def _hilo_heartbeat(
    servidor_ref: list,
    srv_lock: threading.Lock,
    servidores: list[tuple[str, int]],
    config: dict[str, Any],
    terminar: threading.Event,
) -> None:
    """Hilo daemon: envía HEARTBEAT periódicamente y reconecta si el servidor cae."""
    intervalo: float = config["HEARTBEAT_INTERVAL"]
    timeout: float   = config["HEARTBEAT_TIMEOUT"]
    max_fallos: int  = config["MAX_FALLOS"]
    fallos = 0

    while not terminar.wait(intervalo):
        with srv_lock:
            ip, puerto = servidor_ref[0], servidor_ref[1]

        try:
            with socket.create_connection((ip, puerto), timeout=timeout) as s:
                s.sendall(b"HEARTBEAT\n")
                s.shutdown(socket.SHUT_WR)
                resp = s.recv(1024).decode("utf-8").strip()
        except OSError:
            resp = None

        if resp == "HEARTBEAT_ACK":
            fallos = 0
        else:
            fallos += 1
            print(f"[WARN] Heartbeat sin respuesta ({fallos}/{max_fallos})")
            if fallos >= max_fallos:
                nuevo = _intentar_reconexion((ip, puerto), servidores, timeout)
                if nuevo is not None:
                    with srv_lock:
                        servidor_ref[0], servidor_ref[1] = nuevo[0], nuevo[1]
                    print(f"[INFO] Reconectado a {nuevo[0]}:{nuevo[1]}")
                    fallos = 0
                else:
                    print("[INFO] No hay servidores disponibles. Cerrando cliente.")
                    terminar.set()
                    return


# ---------------------------------------------------------------------------
# Bucle principal
# ---------------------------------------------------------------------------

def ejecutar(
    ip_servidor: str,
    puerto: int,
    id_cliente: str,
    servidores: list[str],
    intervalo_default: float = 5.0,
) -> None:
    config = _cargar_config()

    # Lista de servidores conocidos como tuplas (ip, puerto) para el heartbeat
    servidores_tup: list[tuple[str, int]] = [(ip_servidor, puerto)]
    for srv in servidores:
        try:
            ip_s, p_s = srv.rsplit(":", 1)
            entrada = (ip_s, int(p_s))
            if entrada not in servidores_tup:
                servidores_tup.append(entrada)
        except ValueError:
            pass

    # Estado compartido entre bucle principal y hilo de heartbeat
    srv_lock = threading.Lock()
    servidor_ref = [ip_servidor, puerto]  # mutable: [ip, puerto]
    terminar = threading.Event()

    # Arrancar hilo de heartbeat (CU3 / RC6)
    hb = threading.Thread(
        target=_hilo_heartbeat,
        args=(servidor_ref, srv_lock, servidores_tup, config, terminar),
        daemon=True,
    )
    hb.start()

    cpu_anterior = _leer_cpu_snapshot()
    tx_anterior = _tx_bytes_total()
    instante_anterior = time.time()

    # CU2 + RU-5: registro inicial en el servidor
    intervalo = _registrar_cliente(ip_servidor, puerto, id_cliente, servidores, intervalo_default)
    if intervalo is None:
        print("[ERROR] No se ha podido registrar el cliente en el servidor inicial.")
        terminar.set()
        return

    print(
        f"[INFO] Cliente registrado. Servidor: {ip_servidor}:{puerto} "
        f"— intervalo de monitorización: {intervalo}s"
    )

    try:
        while not terminar.is_set():
            with srv_lock:
                ip_act, pto_act = servidor_ref[0], servidor_ref[1]

            metricas, cpu_anterior, tx_anterior, instante_anterior = capturar_metricas(
                id_cliente=id_cliente,
                cpu_anterior=cpu_anterior,
                tx_anterior=tx_anterior,
                instante_anterior=instante_anterior,
            )

            respuesta = _enviar_mensaje(ip_act, pto_act, metricas)
            if respuesta is None:
                print("[WARN] No se ha recibido respuesta del servidor.")
            elif respuesta == "METRICS_OK":
                pass
            elif respuesta.startswith("REASSIGN"):
                nuevo = _parsear_destino(respuesta)
                if nuevo is not None:
                    with srv_lock:
                        servidor_ref[0], servidor_ref[1] = nuevo[0], nuevo[1]
                    print(f"[INFO] Cliente reasignado a {nuevo[0]}:{nuevo[1]}")
                    nuevo_intervalo = _registrar_cliente(
                        nuevo[0], nuevo[1], id_cliente, servidores, intervalo
                    )
                    if nuevo_intervalo is not None:
                        intervalo = nuevo_intervalo

            # wait() en vez de sleep() para poder terminar antes de que expire el intervalo
            terminar.wait(intervalo)

    except KeyboardInterrupt:
        print("\n[INFO] Cliente de monitorización detenido manualmente.")
    finally:
        terminar.set()


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cliente de monitorización (RC1, RC2, RC3, RC6, CU2, CU3, RU-5)"
    )
    parser.add_argument(
        "ip_servidor",
        nargs="?",
        default=None,
        help="IP del servidor inicial. Si se omite, se autodescubre en la red (RC1).",
    )
    parser.add_argument(
        "--puerto",
        type=int,
        default=None,
        help="Puerto TCP del servidor (por defecto, el de config.json)",
    )
    parser.add_argument(
        "--intervalo",
        type=float,
        default=None,
        help="Intervalo de monitorización por defecto (segundos). "
             "El servidor puede sobreescribirlo con MONITOR_REQUEST.",
    )
    parser.add_argument(
        "--id-cliente",
        default=platform.node() or socket.gethostname() or "cliente",
        help="Identificador lógico del cliente",
    )
    parser.add_argument(
        "--servidores",
        nargs="*",
        default=[],
        help="Lista conocida de servidores en formato ip:puerto",
    )
    args = parser.parse_args()

    config = _cargar_config()
    puerto = args.puerto if args.puerto is not None else int(config["PUERTO_TCP"])
    intervalo_default = (
        args.intervalo if args.intervalo is not None
        else float(config.get("MONITOR_INTERVAL", 5))
    )

    ip_servidor = args.ip_servidor
    if ip_servidor is None:
        print("[INFO] No se ha indicado servidor. Buscando en la red local...")
        ip_servidor = _descubrir_servidor(puerto)
        if ip_servidor is None:
            print("[ERROR] No se ha encontrado ningún servidor activo. Cerrando cliente.")
            sys.exit(1)
        print(f"[INFO] Servidor encontrado: {ip_servidor}:{puerto}")

    ejecutar(
        ip_servidor=ip_servidor,
        puerto=puerto,
        id_cliente=args.id_cliente,
        servidores=args.servidores,
        intervalo_default=intervalo_default,
    )
