"""
Utilidades de monitorización del servidor — SRV-5, SRV-7 y SRV-8.

Este módulo encapsula el cálculo de la carga local del servidor y la
escritura del log de datos monitorizados para reutilizarlo desde otros
componentes del sistema.
"""

from __future__ import annotations

import json
import os
import platform
import time
from typing import Any


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


def obtener_metricas_servidor() -> dict[str, Any]:
    meminfo = _leer_meminfo()
    mem_total_kb = meminfo.get("MemTotal", 0)
    mem_disp_kb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
    mem_usada_kb = max(0, mem_total_kb - mem_disp_kb)
    mem_pct = round((mem_usada_kb / mem_total_kb) * 100, 2) if mem_total_kb else 0.0

    try:
        uno, cinco, quince = os.getloadavg()
    except OSError:
        uno = cinco = quince = 0.0

    return {
        "hostname": platform.node(),
        "cores": os.cpu_count() or 1,
        "loadavg_1": round(uno, 2),
        "loadavg_5": round(cinco, 2),
        "loadavg_15": round(quince, 2),
        "memory_usage_pct": mem_pct,
        "timestamp": round(time.time(), 3),
    }


def calcular_carga(
    tiempos_monitorizacion: list[float],
    clientes_activos: int,
) -> dict[str, Any]:
    metricas = obtener_metricas_servidor()

    tiempo_medio = sum(tiempos_monitorizacion) / len(tiempos_monitorizacion) if tiempos_monitorizacion else 0.0
    tiempo_ms = round(tiempo_medio * 1000, 2)

    load_norm = 0.0
    cores = max(1, int(metricas["cores"]))
    load_norm = min(100.0, (metricas["loadavg_1"] / cores) * 100.0)

    puntuacion = round(
        min(
            100.0,
            tiempo_ms * 0.20
            + load_norm * 0.45
            + metricas["memory_usage_pct"] * 0.25
            + clientes_activos * 3.5,
        ),
        2,
    )

    return {
        "score": puntuacion,
        "tiempo_medio_monitorizacion_ms": tiempo_ms,
        "clientes_activos": clientes_activos,
        "hardware": metricas,
    }


def guardar_carga(ruta: str, carga: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(carga, f, ensure_ascii=False, indent=2)


def registrar_datos_monitorizados(ruta: str, datos: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    linea = json.dumps(datos, ensure_ascii=False)
    with open(ruta, "a", encoding="utf-8") as f:
        f.write(linea + "\n")
