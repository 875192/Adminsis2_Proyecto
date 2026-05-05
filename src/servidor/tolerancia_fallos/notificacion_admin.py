"""
Notificación al administrador cuando un cliente cae — RS-10

Implementación real: imprime el mensaje CLIENT_DOWN por consola.
En un despliegue real se sustituiría por email, SNMP o alerta Zabbix.
"""


def notificar_admin(client_ip: str) -> None:
    """Notifica al administrador que el cliente con `client_ip` ha caído."""
    print(f"[ADMIN] CLIENT_DOWN client_ip={client_ip}", flush=True)
