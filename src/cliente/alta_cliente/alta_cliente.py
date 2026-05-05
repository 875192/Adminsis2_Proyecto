#!/usr/bin/env python3

import os
import subprocess
import sys


def run(cmd, quiet=False, capture=False, input_data=None):
    kwargs = {
        "check": True,
        "text": True,
    }
    if quiet:
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
    elif capture:
        kwargs["capture_output"] = True
    if input_data is not None:
        kwargs["input"] = input_data
    return subprocess.run(cmd, **kwargs)


def require_root():
    if os.geteuid() != 0:
        print("Por favor, ejecuta este script como root (sudo).")
        sys.exit(1)


def get_local_network():
    result = run(["ip", "-o", "-f", "inet", "addr", "show"], capture=True)
    for line in result.stdout.splitlines():
        if " scope global " in line:
            parts = line.split()
            if len(parts) >= 4:
                return parts[3]
    return ""


def find_zabbix_server_ip(network):
    result = run(["nmap", "-p", "10051", "--open", network, "-oG", "-"], capture=True)
    for line in result.stdout.splitlines():
        if "10051/open" in line:
            parts = line.split()
            if len(parts) >= 2:
                return parts[1]
    return ""


def main():
    require_root()

    print("=====================================================")
    print("   CASO DE USO 2: INSERCION DE UN NUEVO CLIENTE      ")
    print("=====================================================")

    if len(sys.argv) > 1:
        ip_servidor = sys.argv[1]
        print(f"--> MODO MANUAL: Se ha proporcionado la IP del servidor: {ip_servidor}")
    else:
        print("--> MODO AUTOMATICO: No se proporciono IP. Iniciando descubrimiento en la red...")

        run(["apt-get", "install", "-y", "nmap"], quiet=True)

        red_local = get_local_network()
        print(f"    Escaneando la red local ({red_local}) en busca del puerto 10051 (Zabbix)...")

        ip_servidor = find_zabbix_server_ip(red_local)
        if not ip_servidor:
            print("    [ERROR] No se ha encontrado ningun servidor Zabbix activo en la red.")
            sys.exit(1)

        print(f"--> EXITO! Servidor Zabbix descubierto automaticamente en: {ip_servidor}")

    print("=====================================================")
    print("   INSTALANDO Y CONFIGURANDO AGENTE ZABBIX           ")
    print("=====================================================")

    run([
        "wget",
        "https://repo.zabbix.com/zabbix/7.0/ubuntu/pool/main/z/zabbix-release/zabbix-release_7.0-2+ubuntu24.04_all.deb",
        "-q",
    ])
    run(["dpkg", "-i", "zabbix-release_7.0-2+ubuntu24.04_all.deb"], quiet=True)
    run(["apt", "update"], quiet=True)
    run(["apt", "install", "-y", "zabbix-agent"], quiet=True)

    print(f"--> Vinculando el cliente con el servidor ({ip_servidor})...")
    run(["sed", "-i", f"s/^Server=127.0.0.1/Server={ip_servidor}/", "/etc/zabbix/zabbix_agentd.conf"])
    run(["sed", "-i", f"s/^ServerActive=127.0.0.1/ServerActive={ip_servidor}/", "/etc/zabbix/zabbix_agentd.conf"])

    run(["sed", "-i", "s/^Hostname=Zabbix server/# Hostname=/", "/etc/zabbix/zabbix_agentd.conf"])
    run(["sed", "-i", "/^HostnameItem=/d", "/etc/zabbix/zabbix_agentd.conf"])
    with open("/etc/zabbix/zabbix_agentd.conf", "a", encoding="utf-8") as config_file:
        config_file.write("HostnameItem=system.hostname\n")

    run(["systemctl", "restart", "zabbix-agent"])
    run(["systemctl", "enable", "zabbix-agent"])

    print("=====================================================")
    print("   EL CLIENTE SE HA UNIDO AL SISTEMA Y ESTA          ")
    print("   LISTO PARA SER MONITORIZADO.                      ")
    print("=====================================================")


if __name__ == "__main__":
    main()
