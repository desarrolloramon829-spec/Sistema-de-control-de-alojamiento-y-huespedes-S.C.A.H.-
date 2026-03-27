"""
Sincroniza manualmente las alertas de hoteles sin cargas.

Uso:
    python scripts/sincronizar_alertas_hoteles.py
"""

import os
import sys


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from web.app import create_app
from web.services.alert_service import (
    contar_alertas_pendientes,
    sincronizar_alertas_hoteles_inactivos,
)


def main() -> int:
    app = create_app(os.environ.get("FLASK_ENV", "production"))

    with app.app_context():
        resultado = sincronizar_alertas_hoteles_inactivos()
        pendientes = contar_alertas_pendientes(sincronizar=False)

    if not resultado.get("habilitada"):
        print("Sincronización omitida: la alerta de hoteles inactivos está deshabilitada.")
        return 0

    print("Sincronización de alertas completada.")
    print(f"Umbral de inactividad: {resultado.get('umbral_dias', 0)} días")
    print(f"Alertas vigentes: {resultado.get('vigentes', 0)}")
    print(f"Alertas creadas: {resultado.get('creadas', 0)}")
    print(f"Alertas cerradas: {resultado.get('cerradas', 0)}")
    print(f"Alertas pendientes totales: {pendientes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())