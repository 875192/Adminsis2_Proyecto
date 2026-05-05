"""
Notificación al administrador cuando un cliente cae — RS-10

Envía el mensaje CLIENT_DOWN al nodo administrador por TCP si ADMIN_HOST está
configurado en config.json. Siempre imprime por consola como respaldo.
"""

import socket


def notificar_admin(client_ip: str, admin_host: str = "", admin_puerto: int = 9099) -> None:
    """Notifica la caída de un cliente al administrador.

    Si admin_host está definido, abre una conexión TCP y envía CLIENT_DOWN.
    En cualquier caso imprime el mensaje por consola.
    """
    mensaje = f"CLIENT_DOWN client_ip={client_ip}"

    if admin_host:
        try:
            with socket.create_connection((admin_host, admin_puerto), timeout=3) as s:
                s.sendall((mensaje + "\n").encode("utf-8"))
        except OSError:
            pass

    print(f"[ADMIN] {mensaje}", flush=True)
