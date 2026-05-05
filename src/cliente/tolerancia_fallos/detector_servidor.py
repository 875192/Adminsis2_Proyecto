"""
Detector de caída de servidor — CU3 (Persona 3: Tolerancia a Fallos)

Lógica principal del cliente:
  - Envía HEARTBEAT al servidor asignado cada HEARTBEAT_INTERVAL segundos.
  - Si no recibe HEARTBEAT_ACK en HEARTBEAT_TIMEOUT segundos, cuenta un fallo.
  - Tras MAX_FALLOS consecutivos sin respuesta, declara la caída del servidor.
  - Intenta reconectarse a otro servidor (CU3); al hacerlo informa al nuevo
    servidor del servidor caído para que registre el evento en el log.
  - Si no hay servidores disponibles, termina su ejecución (RU-3).

Uso:
    python detector_servidor.py <ip_servidor> [--servidores ip1:puerto ip2:puerto ...]
"""

import json
import os
import socket
import time
import argparse

from reconexion import intentar_reconexion


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
# Comunicación TCP
# ---------------------------------------------------------------------------

def _enviar_y_recibir(ip: str, puerto: int, mensaje: str, timeout: float) -> str | None:
    try:
        with socket.create_connection((ip, puerto), timeout=timeout) as s:
            s.sendall((mensaje + "\n").encode("utf-8"))
            s.shutdown(socket.SHUT_WR)
            return s.recv(1024).decode("utf-8").strip()
    except (ConnectionRefusedError, TimeoutError, OSError):
        return None


# ---------------------------------------------------------------------------
# Bucle principal
# ---------------------------------------------------------------------------

def ejecutar(servidor_inicial: tuple[str, int], servidores: list[tuple[str, int]]) -> None:
    config = _cargar_config()

    intervalo: float = config["HEARTBEAT_INTERVAL"]
    timeout: float   = config["HEARTBEAT_TIMEOUT"]
    max_fallos: int  = config["MAX_FALLOS"]

    servidor_actual = servidor_inicial
    fallos = 0

    print(f"[INFO] Cliente iniciado. Servidor asignado: {servidor_actual[0]}:{servidor_actual[1]}")

    try:
        while True:
            ip, puerto = servidor_actual
            respuesta = _enviar_y_recibir(ip, puerto, "HEARTBEAT", timeout)

            if respuesta == "HEARTBEAT_ACK":
                fallos = 0
            else:
                fallos += 1
                print(f"[WARN] Sin respuesta del servidor ({fallos}/{max_fallos})")

                if fallos >= max_fallos:
                    print(f"[INFO] Servidor caído: {ip}. Iniciando reconexión.")

                    nuevo = intentar_reconexion(
                        servidor_caido=servidor_actual,
                        servidores=servidores,
                        heartbeat_timeout=timeout,
                    )

                    if nuevo is not None:
                        print(f"[INFO] Reconectado a nuevo servidor: {nuevo[0]}:{nuevo[1]}")
                        servidor_actual = nuevo
                        fallos = 0
                    else:
                        print("[INFO] No hay servidores disponibles. Cerrando cliente.")
                        break

            time.sleep(intervalo)

    except KeyboardInterrupt:
        print("\n[INFO] Cliente detenido manualmente.")


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def _parsear_servidores(textos: list[str]) -> list[tuple[str, int]]:
    resultado = []
    for texto in textos:
        try:
            ip, puerto_txt = texto.split(":", 1)
            resultado.append((ip, int(puerto_txt)))
        except ValueError:
            print(f"[WARN] Formato inválido de servidor ignorado: {texto!r}")
    return resultado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detector de caída de servidor (CU3)")
    parser.add_argument("ip_servidor", help="IP del servidor inicial")
    parser.add_argument(
        "--servidores",
        nargs="*",
        default=[],
        help="Servidores conocidos en formato ip:puerto (para reconexión)",
    )
    args = parser.parse_args()

    config = _cargar_config()
    puerto = int(config["PUERTO_TCP"])
    servidor_inicial = (args.ip_servidor, puerto)

    servidores_conocidos = [servidor_inicial]
    for entrada in _parsear_servidores(args.servidores):
        if entrada not in servidores_conocidos:
            servidores_conocidos.append(entrada)

    ejecutar(servidor_inicial, servidores_conocidos)
