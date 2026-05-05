"""
Lógica de reconexión del cliente a un nuevo servidor (CU3).

Cuando el cliente detecta que su servidor actual ha caído, este módulo
busca otro servidor disponible en la lista y establece una nueva conexión.
"""

import socket


def _enviar_y_recibir(ip: str, puerto: int, mensaje: str, timeout: float) -> str | None:
    try:
        with socket.create_connection((ip, puerto), timeout=timeout) as s:
            s.sendall((mensaje + "\n").encode("utf-8"))
            s.shutdown(socket.SHUT_WR)
            return s.recv(1024).decode("utf-8").strip()
    except (ConnectionRefusedError, TimeoutError, OSError):
        return None


def intentar_reconexion(
    servidor_caido: tuple[str, int],
    servidores: list[tuple[str, int]],
    heartbeat_timeout: float,
) -> tuple[str, int] | None:
    """
    Intenta conectar el cliente a un servidor alternativo.

    Parámetros
    ----------
    servidor_caido : tuple[str, int]
        IP y puerto del servidor que ha caído (se excluye de la búsqueda).
    servidores : list[tuple[str, int]]
        Lista completa de servidores conocidos.
    heartbeat_timeout : float
        Segundos máximos de espera por respuesta del nuevo servidor.

    Retorna
    -------
    tuple[str, int] | None
        El nuevo servidor (ip, puerto) si la reconexión tuvo éxito,
        o None si no queda ningún servidor disponible.
    """
    candidatos = [s for s in servidores if s != servidor_caido]

    for ip, puerto in candidatos:
        respuesta = _enviar_y_recibir(
            ip, puerto,
            f"RECONNECT_REQUEST client server_caido={servidor_caido[0]}",
            heartbeat_timeout,
        )
        if respuesta == "RECONNECT_OK":
            return (ip, puerto)

    return None
