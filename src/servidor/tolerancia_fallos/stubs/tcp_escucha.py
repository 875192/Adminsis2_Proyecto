"""
Stub del listener TCP que implementará Persona 2 (lado servidor).

El servidor real de Persona 2 escuchará en PUERTO_TCP y recibirá
mensajes HEARTBEAT de los clientes conectados. Este stub los simula
en memoria usando hilos de fondo.

Cuando Persona 2 entregue su módulo, sustituir el import en monitor_clientes.py:

    # Stub (desarrollo):
    from stubs.tcp_escucha import EscuchaTCP

    # Real (integración):
    from comunicacion.tcp_escucha import EscuchaTCP

La interfaz (métodos y firmas) debe mantenerse igual.
"""

import queue
import threading


class EscuchaTCP:
    """
    Simula en memoria el listener TCP que proveerá Persona 2.

    Parámetros
    ----------
    clientes : list[str]
        IPs de los clientes que se simula que están enviando heartbeats.
    intervalo : float
        Segundos entre heartbeats de cada cliente (debe coincidir con
        HEARTBEAT_INTERVAL del config).
    modo_fallo : dict[str, int]
        Mapa {ip_cliente: n} — el cliente con esa IP deja de enviar
        heartbeats tras n mensajes enviados. Usado para probar CU4.
        Ejemplo: {"192.168.1.20": 3}
    """

    def __init__(
        self,
        clientes: list[str],
        intervalo: float = 5.0,
        modo_fallo: dict[str, int] | None = None,
    ):
        self._clientes = clientes
        self._intervalo = intervalo
        self._modo_fallo = modo_fallo or {}
        self._buzón: queue.Queue = queue.Queue()
        self._activo = True
        self._contadores: dict[str, int] = {ip: 0 for ip in clientes}

        for ip in clientes:
            hilo = threading.Thread(
                target=self._generar_heartbeats,
                args=(ip,),
                daemon=True,
            )
            hilo.start()

    # ------------------------------------------------------------------
    # Interfaz pública (la misma que tendrá el listener real de Persona 2)
    # ------------------------------------------------------------------

    def siguiente_heartbeat(self, timeout: float) -> tuple[str, str] | None:
        """
        Espera hasta `timeout` segundos por un HEARTBEAT entrante.

        Retorna
        -------
        tuple[str, str] | None
            (ip_cliente, "HEARTBEAT") si llega alguno, o None si timeout.
        """
        try:
            return self._buzón.get(timeout=timeout)
        except queue.Empty:
            return None

    def cerrar(self) -> None:
        """Para la escucha y libera recursos."""
        self._activo = False

    # ------------------------------------------------------------------
    # Lógica interna del stub
    # ------------------------------------------------------------------

    def _generar_heartbeats(self, ip: str) -> None:
        import time

        while self._activo:
            limite = self._modo_fallo.get(ip)
            if limite is not None and self._contadores[ip] >= limite:
                break

            self._contadores[ip] += 1
            self._buzón.put((ip, "HEARTBEAT"))
            time.sleep(self._intervalo)
