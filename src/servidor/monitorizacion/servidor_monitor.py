"""
Servidor de monitorización — SRV-5, SRV-7, SRV-8 y SRV-9 (Persona 4)

Responsabilidades:
  - Registrar clientes dados de alta (RU4).
  - Recibir métricas por TCP y almacenar la información monitorizada.
  - Calcular la carga del servidor combinando tiempo de monitorización
    y recursos hardware disponibles.
  - Reasignar clientes a otro servidor cuando exista uno con menor carga.
  - Mantener compatibilidad básica con los mensajes HEARTBEAT y
    RECONNECT_REQUEST usados por los módulos de tolerancia a fallos.

Uso:
    python servidor_monitor.py --host 0.0.0.0 --puerto 9000 --id srv1
    python servidor_monitor.py --host 0.0.0.0 --puerto 9001 --id srv2 \
        --servidores 127.0.0.1:9000 127.0.0.1:9001
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import socketserver
import sys
import threading
import time
from typing import Any

from logger import _log
from metricas import calcular_carga, guardar_carga, registrar_datos_monitorizados


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

def _cargar_config() -> dict[str, Any]:
    ruta = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "config", "config.json"
    )
    with open(os.path.normpath(ruta), encoding="utf-8") as f:
        return json.load(f)


def _ruta_log_eventos(config: dict[str, Any]) -> str:
    return os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", config["LOG_PATH"])
    )


def _ruta_log_datos() -> str:
    return os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "logs", "datos_monitorizados.log")
    )


def _ruta_carga(id_servidor: str, puerto: int) -> str:
    nombre = f"carga_{id_servidor}_{puerto}.json"
    return os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "logs", nombre)
    )


# ---------------------------------------------------------------------------
# Estado compartido
# ---------------------------------------------------------------------------

class EstadoMonitor:
    def __init__(
        self,
        id_servidor: str,
        host: str,
        puerto: int,
        servidores: list[tuple[str, int]],
        config: dict[str, Any],
        umbral_reasignacion: float,
    ) -> None:
        self.id_servidor = id_servidor
        self.host = host
        self.puerto = puerto
        self.servidores = [s for s in servidores if s != (host, puerto)]
        self.config = config
        self.umbral_reasignacion = umbral_reasignacion
        self.ruta_eventos = _ruta_log_eventos(config)
        self.ruta_datos = _ruta_log_datos()
        self.ruta_carga = _ruta_carga(id_servidor, puerto)
        self.lock = threading.Lock()
        self.clientes: dict[str, dict[str, Any]] = {}
        self.tiempos_monitorizacion: list[float] = []

    def registrar_cliente(self, client_id: str, client_ip: str, known_servers: list[str]) -> None:
        with self.lock:
            self.clientes.setdefault(
                client_id,
                {
                    "client_ip": client_ip,
                    "last_seen": time.time(),
                    "known_servers": known_servers,
                    "metrics": None,
                },
            )
        _log(self.ruta_eventos, "ALTA_CLIENTE", f"client_id={client_id} client_ip={client_ip}")

    def actualizar_metricas(self, client_id: str, payload: dict[str, Any], tiempo: float) -> None:
        with self.lock:
            if client_id not in self.clientes:
                self.clientes[client_id] = {
                    "client_ip": payload.get("client_ip", "desconocida"),
                    "last_seen": time.time(),
                    "known_servers": payload.get("known_servers", []),
                    "metrics": payload,
                }
            else:
                self.clientes[client_id]["last_seen"] = time.time()
                self.clientes[client_id]["metrics"] = payload
            self.tiempos_monitorizacion.append(tiempo)
            if len(self.tiempos_monitorizacion) > 50:
                self.tiempos_monitorizacion.pop(0)

        registrar_datos_monitorizados(self.ruta_datos, payload)

    def obtener_carga(self) -> dict[str, Any]:
        with self.lock:
            carga = calcular_carga(
                tiempos_monitorizacion=list(self.tiempos_monitorizacion),
                clientes_activos=len(self.clientes),
            )
        guardar_carga(self.ruta_carga, carga)
        return carga

    def candidato_reasignacion(self) -> tuple[str, int] | None:
        carga_local = self.obtener_carga()["score"]
        mejor: tuple[str, int] | None = None
        mejor_carga = carga_local

        for ip, puerto in self.servidores:
            carga_remota = _consultar_carga(ip, puerto)
            if carga_remota is None:
                continue
            if carga_remota + self.umbral_reasignacion < mejor_carga:
                mejor = (ip, puerto)
                mejor_carga = carga_remota

        return mejor


# ---------------------------------------------------------------------------
# Comunicación TCP
# ---------------------------------------------------------------------------

def _consultar_carga(ip: str, puerto: int) -> float | None:
    try:
        with socket.create_connection((ip, puerto), timeout=2) as sock:
            sock.sendall(b"LOAD_REQUEST\n")
            sock.shutdown(socket.SHUT_WR)
            respuesta = sock.recv(4096).decode("utf-8").strip()
    except OSError:
        return None

    if not respuesta.startswith("LOAD_RESPONSE "):
        return None

    try:
        return float(respuesta.split()[1])
    except (IndexError, ValueError):
        return None


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


class _Handler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        estado: EstadoMonitor = self.server.estado  # type: ignore[attr-defined]
        inicio = time.monotonic()

        try:
            datos = self.request.recv(65535)
        except OSError:
            return

        if not datos:
            return

        mensaje = datos.decode("utf-8").strip()

        if mensaje == "HEARTBEAT":
            self.request.sendall(b"HEARTBEAT_ACK")
            return

        if mensaje.startswith("RECONNECT_REQUEST"):
            self.request.sendall(b"RECONNECT_OK")
            return

        if mensaje == "LOAD_REQUEST":
            score = estado.obtener_carga()["score"]
            self.request.sendall(f"LOAD_RESPONSE {score}".encode("utf-8"))
            return

        try:
            payload = json.loads(mensaje)
        except json.JSONDecodeError:
            self.request.sendall(b"ERROR")
            return

        tipo = payload.get("type")
        if tipo == "REGISTER":
            estado.registrar_cliente(
                client_id=payload.get("client_id", "cliente"),
                client_ip=payload.get("client_ip", self.client_address[0]),
                known_servers=payload.get("known_servers", []),
            )
            self.request.sendall(b"REGISTER_OK")
            return

        if tipo == "METRICS":
            client_id = payload.get("client_id", self.client_address[0])
            tiempo = time.monotonic() - inicio
            estado.actualizar_metricas(client_id=client_id, payload=payload, tiempo=tiempo)

            mejor = estado.candidato_reasignacion()
            if mejor is not None:
                ip, puerto = mejor
                _log(
                    estado.ruta_eventos,
                    "REASIGNACION",
                    f"client_id={client_id} nuevo_servidor={ip}:{puerto}",
                )
                self.request.sendall(f"REASSIGN {ip} {puerto}".encode("utf-8"))
            else:
                self.request.sendall(b"METRICS_OK")
            return

        self.request.sendall(b"ERROR")


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def _parsear_servidores(textos: list[str]) -> list[tuple[str, int]]:
    servidores = []
    for texto in textos:
        try:
            ip, puerto_txt = texto.split(":", 1)
            servidores.append((ip, int(puerto_txt)))
        except ValueError:
            continue
    return servidores


def ejecutar(
    host: str,
    puerto: int,
    id_servidor: str,
    servidores: list[tuple[str, int]],
    umbral_reasignacion: float,
) -> None:
    config = _cargar_config()
    estado = EstadoMonitor(
        id_servidor=id_servidor,
        host=host,
        puerto=puerto,
        servidores=servidores,
        config=config,
        umbral_reasignacion=umbral_reasignacion,
    )

    with _ThreadingTCPServer((host, puerto), _Handler) as servidor:
        servidor.estado = estado  # type: ignore[attr-defined]
        print(f"[INFO] Servidor {id_servidor} escuchando en {host}:{puerto}")
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            print("\n[INFO] Servidor de monitorización detenido manualmente.")
        finally:
            servidor.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Servidor de monitorización")
    parser.add_argument("--host", default="0.0.0.0", help="IP en la que escuchar")
    parser.add_argument("--puerto", type=int, default=None, help="Puerto TCP")
    parser.add_argument("--id", dest="id_servidor", default="srv1", help="Identificador lógico")
    parser.add_argument(
        "--servidores",
        nargs="*",
        default=[],
        help="Servidores conocidos en formato ip:puerto",
    )
    parser.add_argument(
        "--umbral-reasignacion",
        type=float,
        default=15.0,
        help="Diferencia mínima de carga para reasignar un cliente",
    )
    args = parser.parse_args()

    config = _cargar_config()
    puerto = args.puerto if args.puerto is not None else int(config["PUERTO_TCP"])
    ejecutar(
        host=args.host,
        puerto=puerto,
        id_servidor=args.id_servidor,
        servidores=_parsear_servidores(args.servidores),
        umbral_reasignacion=args.umbral_reasignacion,
    )
