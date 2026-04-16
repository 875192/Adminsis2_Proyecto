"""
Stub de la notificación al administrador (SRV-10).

En el sistema real esto podría ser un email, un mensaje SNMP, una alerta
en Zabbix, etc. El stub simplemente imprime por consola.

Cuando se acuerde el canal de notificación real, sustituir el import:

    # Stub (desarrollo):
    from stubs.notificacion_admin import notificar_admin

    # Real (integración):
    from monitorizacion.notificacion_admin import notificar_admin

La firma de la función debe mantenerse igual.
"""


def notificar_admin(client_ip: str) -> None:
    """
    Notifica al administrador que el cliente con `client_ip` ha caído.

    Parámetros
    ----------
    client_ip : str
        IP del cliente caído.
    """
    print(f"[ADMIN] CLIENT_DOWN client_ip={client_ip}")
