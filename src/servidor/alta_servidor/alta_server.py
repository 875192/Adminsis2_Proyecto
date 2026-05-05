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


def import_zabbix_schema():
    zcat = subprocess.Popen(
        ["zcat", "/usr/share/zabbix-sql-scripts/mysql/server.sql.gz"],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        run(
            [
                "mysql",
                "--default-character-set=utf8mb4",
                "-uzabbix",
                "-pZabbix_Pass1",
                "zabbix",
            ],
            input_data=zcat.stdout.read() if zcat.stdout else "",
        )
    finally:
        zcat.wait()


def main():
    require_root()

    print("=====================================================")
    print("   CASO DE USO 1: INSERCION DE UN NUEVO SERVIDOR     ")
    print("=====================================================")

    run([
        "wget",
        "https://repo.zabbix.com/zabbix/7.0/ubuntu/pool/main/z/zabbix-release/zabbix-release_7.0-2+ubuntu24.04_all.deb",
    ])
    run(["dpkg", "-i", "zabbix-release_7.0-2+ubuntu24.04_all.deb"])
    run(["apt", "update"])
    run([
        "apt",
        "install",
        "-y",
        "zabbix-server-mysql",
        "zabbix-frontend-php",
        "zabbix-apache-conf",
        "zabbix-sql-scripts",
        "zabbix-agent",
    ])

    if len(sys.argv) == 1:
        print("--> MODO MAESTRO: No se detecto argumento. Instalando Base de Datos local...")

        run(["apt", "install", "-y", "mariadb-server"])
        run(["systemctl", "start", "mariadb"])
        run(["systemctl", "enable", "mariadb"])

        run(["mysql", "-e", "CREATE DATABASE zabbix character set utf8mb4 collate utf8mb4_bin;"])
        run(["mysql", "-e", "CREATE USER 'zabbix'@'%' IDENTIFIED BY 'Zabbix_Pass1';"])
        run(["mysql", "-e", "GRANT ALL PRIVILEGES ON zabbix.* TO 'zabbix'@'%';"])
        run(["mysql", "-e", "SET GLOBAL log_bin_trust_function_creators = 1;"])

        import_zabbix_schema()

        run(["mysql", "-e", "SET GLOBAL log_bin_trust_function_creators = 0;"])

        run([
            "sed",
            "-i",
            "s/^bind-address.*/bind-address = 0.0.0.0/",
            "/etc/mysql/mariadb.conf.d/50-server.cnf",
        ])
        run(["systemctl", "restart", "mariadb"])

        run([
            "sed",
            "-i",
            "s/# DBPassword=/DBPassword=Zabbix_Pass1/",
            "/etc/zabbix/zabbix_server.conf",
        ])

        print("--> SERVIDOR MAESTRO CONFIGURADO.")
    else:
        ip_maestro = sys.argv[1]
        print(f"--> MODO SECUNDARIO: Conectando a la base de datos del Maestro en {ip_maestro}...")

        run([
            "sed",
            "-i",
            f"s/^DBHost=localhost/DBHost={ip_maestro}/",
            "/etc/zabbix/zabbix_server.conf",
        ])
        run([
            "sed",
            "-i",
            "s/# DBPassword=/DBPassword=Zabbix_Pass1/",
            "/etc/zabbix/zabbix_server.conf",
        ])
        run([
            "sed",
            "-i",
            "s/# AllowUnsupportedDBVersions=0/AllowUnsupportedDBVersions=1/",
            "/etc/zabbix/zabbix_server.conf",
        ])

        php_config = (
            "<?php\n"
            "global $DB, $HISTORY;\n"
            f"$DB['TYPE']     = 'MYSQL';\n"
            f"$DB['SERVER']   = '{ip_maestro}';\n"
            "$DB['PORT']     = '0';\n"
            "$DB['DATABASE'] = 'zabbix';\n"
            "$DB['USER']     = 'zabbix';\n"
            "$DB['PASSWORD'] = 'Zabbix_Pass1';\n"
            "$DB['ALLOW_UNSUPPORTED'] = true;\n"
            "$ZBX_SERVER      = 'localhost';\n"
            "$ZBX_SERVER_PORT = '10051';\n"
            "$ZBX_SERVER_NAME = 'Nodo Zabbix Secundario';\n"
            "$IMAGE_FORMAT_DEFAULT = IMAGE_FORMAT_PNG;\n"
            "?>\n"
        )
        with open("/etc/zabbix/web/zabbix.conf.php", "w", encoding="utf-8") as php_file:
            php_file.write(php_config)
        run(["chown", "www-data:www-data", "/etc/zabbix/web/zabbix.conf.php"])

        print("--> NODO SECUNDARIO VINCULADO.")

    run(["systemctl", "restart", "zabbix-server", "zabbix-agent", "apache2"])
    run(["systemctl", "enable", "zabbix-server", "zabbix-agent", "apache2"])

    print("=====================================================")
    print("   EL SERVIDOR SE HA UNIDO AL SISTEMA Y ESTA         ")
    print("   EN ESTADO DE MONITORIZACION.                      ")
    print("=====================================================")


if __name__ == "__main__":
    main()
