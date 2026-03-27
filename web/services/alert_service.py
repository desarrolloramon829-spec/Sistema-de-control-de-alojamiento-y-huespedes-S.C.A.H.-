"""
S.C.A.H. Web - Servicio de Alertas Operativas
Detección, persistencia y consulta de alertas vinculadas a huéspedes.
"""

import json
import os
import sys
from datetime import date, datetime

import psycopg2.extras

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import (
    ALERT_ENABLED_TYPES,
    ALERT_HOTEL_INACTIVITY_DAYS,
    ALERT_TYPE_SETTINGS,
    ALERT_WINDOW_HOURS,
)
from database.connection import db
from utils.validators import sanitizar_texto

ALERTA_DUPLICADO_EXACTO = "duplicado_exacto"
ALERTA_DUPLICADO_LOTE = "duplicado_en_lote"
ALERTA_MISMO_HOTEL = "mismo_sujeto_mismo_hotel"
ALERTA_HOTELES_CERCANOS = "sujeto_en_hoteles_distintos_lapso_corto"
ALERTA_HOTEL_SIN_CARGAS = "hotel_sin_cargas_inactivo"


def normalizar_documento(valor: str) -> str:
    if not valor:
        return ""
    return "".join(char for char in str(valor).upper().strip() if char.isalnum())


def normalizar_telefono(valor: str) -> str:
    if not valor:
        return ""
    return "".join(char for char in str(valor) if char.isdigit())


def _normalizar_nombre(valor: str) -> str:
    return sanitizar_texto(valor or "").strip().lower()


def _serializar_payload(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _deserializar_payload(payload_json) -> dict:
    if not payload_json:
        return {}
    if isinstance(payload_json, dict):
        return payload_json
    try:
        return json.loads(payload_json)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def _fecha_iso(valor) -> str:
    if isinstance(valor, datetime):
        valor = valor.date()
    if isinstance(valor, date):
        return valor.isoformat()
    return ""


def _fecha_desde_payload(valor):
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return datetime.fromisoformat(str(valor)).date()
    except ValueError:
        return None


def _hours_between(fecha_a, fecha_b) -> int | None:
    if not fecha_a or not fecha_b:
        return None
    if isinstance(fecha_a, datetime):
        fecha_a = fecha_a.date()
    if isinstance(fecha_b, datetime):
        fecha_b = fecha_b.date()
    if not isinstance(fecha_a, date) or not isinstance(fecha_b, date):
        return None
    return abs((fecha_a - fecha_b).days) * 24


def _rangos_superpuestos(entrada_a, salida_a, entrada_b, salida_b) -> bool:
    if not entrada_a or not entrada_b:
        return False
    salida_a = salida_a or entrada_a
    salida_b = salida_b or entrada_b
    return entrada_a <= salida_b and salida_a >= entrada_b


def _crear_alerta(tipo: str, severidad: str, resumen: str, bloqueante: bool, **extra) -> dict:
    if tipo not in ALERT_ENABLED_TYPES:
        return None

    tipo_config = ALERT_TYPE_SETTINGS.get(tipo, {})
    alerta = {
        "tipo": tipo,
        "tipo_label": tipo_config.get("label", tipo.replace("_", " ").title()),
        "severidad": tipo_config.get("severidad", severidad),
        "resumen": resumen,
        "bloqueante": tipo_config.get("bloqueante", bloqueante),
    }
    alerta.update(extra)
    return alerta


def _crear_estado_lote() -> dict:
    return {
        "exactos": {},
        "por_documento": {},
        "por_telefono": {},
        "por_nombre": {},
    }


def _registrar_en_lote(estado_lote: dict, huesped: dict, hotel_ref: str):
    documento = normalizar_documento(huesped.get("dni_pasaporte"))
    telefono = normalizar_telefono(huesped.get("telefono"))
    nombre = _normalizar_nombre(huesped.get("apellido_nombre"))
    fecha_entrada = huesped.get("fecha_entrada")
    payload = {
        "documento": documento,
        "telefono": telefono,
        "nombre": nombre,
        "fecha_entrada": fecha_entrada,
        "fecha_salida": huesped.get("fecha_salida"),
        "hotel": hotel_ref,
        "apellido_nombre": huesped.get("apellido_nombre", ""),
    }

    if documento and fecha_entrada:
        estado_lote["exactos"][(hotel_ref, documento, fecha_entrada)] = payload
        estado_lote["por_documento"].setdefault(documento, []).append(payload)
    if telefono:
        estado_lote["por_telefono"].setdefault((hotel_ref, telefono), []).append(payload)
    if nombre:
        estado_lote["por_nombre"].setdefault((hotel_ref, nombre), []).append(payload)


def _alertas_lote(huesped: dict, hotel_ref: str, estado_lote: dict) -> list:
    alertas = []
    documento = normalizar_documento(huesped.get("dni_pasaporte"))
    telefono = normalizar_telefono(huesped.get("telefono"))
    nombre = _normalizar_nombre(huesped.get("apellido_nombre"))
    fecha_entrada = huesped.get("fecha_entrada")
    fecha_salida = huesped.get("fecha_salida")

    if documento and fecha_entrada:
        previo = estado_lote["exactos"].get((hotel_ref, documento, fecha_entrada))
        if previo:
            alertas.append(
                _crear_alerta(
                    ALERTA_DUPLICADO_LOTE,
                    "critical",
                    "El mismo documento ya aparece en este lote para el mismo hotel y fecha de entrada.",
                    True,
                    hotel_relacionado=previo.get("hotel"),
                    coincidencia="documento_lote",
                )
            )

        for previo in estado_lote["por_documento"].get(documento, []):
            if previo.get("hotel") != hotel_ref:
                horas = _hours_between(fecha_entrada, previo.get("fecha_salida") or previo.get("fecha_entrada"))
                if horas is not None and horas <= ALERT_WINDOW_HOURS:
                    alertas.append(
                        _crear_alerta(
                            ALERTA_HOTELES_CERCANOS,
                            "danger",
                            f"El documento ya aparece en otro hotel del mismo lote dentro de {horas} horas.",
                            False,
                            hotel_relacionado=previo.get("hotel"),
                            horas_lapso=horas,
                            coincidencia="documento_lote_hoteles",
                        )
                    )
                    break

    if telefono and estado_lote["por_telefono"].get((hotel_ref, telefono)):
        alertas.append(
            _crear_alerta(
                ALERTA_MISMO_HOTEL,
                "warning",
                "El teléfono ya figura en este lote para el mismo hotel.",
                False,
                coincidencia="telefono_lote",
            )
        )

    if nombre:
        for previo in estado_lote["por_nombre"].get((hotel_ref, nombre), []):
            if _rangos_superpuestos(
                fecha_entrada,
                fecha_salida,
                previo.get("fecha_entrada"),
                previo.get("fecha_salida"),
            ):
                alertas.append(
                    _crear_alerta(
                        ALERTA_MISMO_HOTEL,
                        "warning",
                        "El mismo nombre ya aparece en este lote con fechas superpuestas para el mismo hotel.",
                        False,
                        coincidencia="nombre_solapado_lote",
                    )
                )
                break

    return alertas


def _buscar_duplicados_existentes(conn, huesped: dict, hotel_id: int | None, hotel_nombre: str) -> list:
    alertas = []
    documento = normalizar_documento(huesped.get("dni_pasaporte"))
    telefono = normalizar_telefono(huesped.get("telefono"))
    nombre = _normalizar_nombre(huesped.get("apellido_nombre"))
    fecha_entrada = huesped.get("fecha_entrada")
    fecha_salida = huesped.get("fecha_salida")

    if not documento and not nombre and not telefono:
        return alertas

    cursor = _dict_cursor(conn)
    try:
        if documento and hotel_id and fecha_entrada:
            cursor.execute(
                """
                SELECT h.id, h.fecha_entrada, h.fecha_salida, ht.nombre AS hotel
                FROM huespedes h
                JOIN hoteles ht ON ht.id = h.hotel_id
                WHERE h.hotel_id = %s
                  AND regexp_replace(upper(COALESCE(h.dni_pasaporte, '')), '[^A-Z0-9]', '', 'g') = %s
                  AND h.fecha_entrada = %s
                ORDER BY h.fecha_registro DESC
                LIMIT 1
                """,
                (hotel_id, documento, fecha_entrada),
            )
            exacto = cursor.fetchone()
            if exacto:
                alertas.append(
                    _crear_alerta(
                        ALERTA_DUPLICADO_EXACTO,
                        "critical",
                        "Ya existe un huésped con el mismo documento, hotel y fecha de entrada.",
                        True,
                        hotel_relacionado=exacto.get("hotel"),
                        huesped_relacionado_id=exacto.get("id"),
                        coincidencia="documento_hotel_fecha",
                    )
                )

        if documento and hotel_id:
            cursor.execute(
                """
                SELECT h.id, h.fecha_entrada, h.fecha_salida, ht.nombre AS hotel
                FROM huespedes h
                JOIN hoteles ht ON ht.id = h.hotel_id
                WHERE h.hotel_id = %s
                  AND regexp_replace(upper(COALESCE(h.dni_pasaporte, '')), '[^A-Z0-9]', '', 'g') = %s
                ORDER BY h.fecha_registro DESC
                LIMIT 5
                """,
                (hotel_id, documento),
            )
            for fila in cursor.fetchall():
                if _rangos_superpuestos(fecha_entrada, fecha_salida, fila.get("fecha_entrada"), fila.get("fecha_salida")):
                    alertas.append(
                        _crear_alerta(
                            ALERTA_MISMO_HOTEL,
                            "warning",
                            "El mismo documento ya registra una estadía superpuesta en este hotel.",
                            False,
                            hotel_relacionado=fila.get("hotel"),
                            huesped_relacionado_id=fila.get("id"),
                            coincidencia="documento_mismo_hotel",
                        )
                    )
                    break

        if nombre and hotel_id and fecha_entrada:
            cursor.execute(
                """
                SELECT h.id, h.fecha_entrada, h.fecha_salida, ht.nombre AS hotel
                FROM huespedes h
                JOIN hoteles ht ON ht.id = h.hotel_id
                WHERE h.hotel_id = %s
                  AND LOWER(TRIM(COALESCE(h.apellido_nombre, ''))) = %s
                ORDER BY h.fecha_registro DESC
                LIMIT 5
                """,
                (hotel_id, nombre),
            )
            for fila in cursor.fetchall():
                if _rangos_superpuestos(fecha_entrada, fecha_salida, fila.get("fecha_entrada"), fila.get("fecha_salida")):
                    alertas.append(
                        _crear_alerta(
                            ALERTA_MISMO_HOTEL,
                            "warning",
                            "El mismo nombre ya tiene una estadía superpuesta en este hotel.",
                            False,
                            hotel_relacionado=fila.get("hotel"),
                            huesped_relacionado_id=fila.get("id"),
                            coincidencia="nombre_mismo_hotel",
                        )
                    )
                    break

        if telefono and hotel_id:
            cursor.execute(
                """
                SELECT h.id, ht.nombre AS hotel
                FROM huespedes h
                JOIN hoteles ht ON ht.id = h.hotel_id
                WHERE h.hotel_id = %s
                  AND regexp_replace(COALESCE(h.telefono, ''), '[^0-9]', '', 'g') = %s
                ORDER BY h.fecha_registro DESC
                LIMIT 1
                """,
                (hotel_id, telefono),
            )
            fila = cursor.fetchone()
            if fila:
                alertas.append(
                    _crear_alerta(
                        ALERTA_MISMO_HOTEL,
                        "warning",
                        "El teléfono ya figura asociado a una estadía en este hotel.",
                        False,
                        hotel_relacionado=fila.get("hotel"),
                        huesped_relacionado_id=fila.get("id"),
                        coincidencia="telefono_mismo_hotel",
                    )
                )

        if documento and fecha_entrada:
            params = [documento]
            hotel_clause = ""
            if hotel_id:
                hotel_clause = "AND h.hotel_id <> %s"
                params.append(hotel_id)
            cursor.execute(
                f"""
                SELECT h.id, h.fecha_entrada, h.fecha_salida, ht.nombre AS hotel
                FROM huespedes h
                JOIN hoteles ht ON ht.id = h.hotel_id
                WHERE regexp_replace(upper(COALESCE(h.dni_pasaporte, '')), '[^A-Z0-9]', '', 'g') = %s
                  {hotel_clause}
                ORDER BY h.fecha_registro DESC
                LIMIT 10
                """,
                tuple(params),
            )
            for fila in cursor.fetchall():
                horas = _hours_between(fecha_entrada, fila.get("fecha_salida") or fila.get("fecha_entrada"))
                if horas is not None and horas <= ALERT_WINDOW_HOURS:
                    resumen = (
                        f"El mismo documento aparece en {fila.get('hotel')} y {hotel_nombre or 'el hotel de destino'} "
                        f"con una diferencia estimada de {horas} horas."
                    )
                    alertas.append(
                        _crear_alerta(
                            ALERTA_HOTELES_CERCANOS,
                            "danger",
                            resumen,
                            False,
                            hotel_relacionado=fila.get("hotel"),
                            huesped_relacionado_id=fila.get("id"),
                            horas_lapso=horas,
                            coincidencia="documento_hoteles_distintos",
                        )
                    )
                    break
                if _rangos_superpuestos(fecha_entrada, fecha_salida, fila.get("fecha_entrada"), fila.get("fecha_salida")):
                    alertas.append(
                        _crear_alerta(
                            ALERTA_HOTELES_CERCANOS,
                            "danger",
                            f"El mismo documento presenta una estadía superpuesta entre {fila.get('hotel')} y {hotel_nombre or 'el hotel de destino'}.",
                            False,
                            hotel_relacionado=fila.get("hotel"),
                            huesped_relacionado_id=fila.get("id"),
                            coincidencia="documento_hoteles_superpuestos",
                        )
                    )
                    break
    finally:
        cursor.close()

    return _deduplicar_alertas(alertas)


def _deduplicar_alertas(alertas: list) -> list:
    vistos = set()
    resultado = []
    for alerta in alertas:
        if not alerta:
            continue
        clave = (
            alerta.get("tipo"),
            alerta.get("coincidencia"),
            alerta.get("hotel_relacionado"),
            alerta.get("huesped_relacionado_id"),
            alerta.get("horas_lapso"),
        )
        if clave in vistos:
            continue
        vistos.add(clave)
        resultado.append(alerta)
    return resultado


def _alertas_hoteles_inactivos_habilitadas() -> bool:
    return (
        ALERT_HOTEL_INACTIVITY_DAYS > 0
        and ALERTA_HOTEL_SIN_CARGAS in ALERT_ENABLED_TYPES
    )


def sincronizar_alertas_hoteles_inactivos() -> dict:
    resultado = {
        "habilitada": _alertas_hoteles_inactivos_habilitadas(),
        "vigentes": 0,
        "creadas": 0,
        "cerradas": 0,
        "umbral_dias": ALERT_HOTEL_INACTIVITY_DAYS,
    }

    if not _alertas_hoteles_inactivos_habilitadas():
        return resultado

    conn = db.obtener_conexion()
    if not conn:
        return resultado

    cursor = _dict_cursor(conn)
    hoy = date.today()
    alertas_vigentes = set()
    alertas_creadas = 0
    alertas_cerradas = 0

    try:
        cursor.execute(
            """
            SELECT
                ht.id,
                ht.nombre,
                ht.fecha_registro::date AS fecha_registro_hotel,
                MAX(h.fecha_registro)::date AS fecha_ultima_carga
            FROM hoteles ht
            LEFT JOIN huespedes h ON h.hotel_id = ht.id
            WHERE ht.activo = TRUE
            GROUP BY ht.id, ht.nombre, ht.fecha_registro
            ORDER BY ht.nombre ASC
            """
        )

        for hotel in cursor.fetchall() or []:
            fecha_base = hotel.get("fecha_ultima_carga") or hotel.get("fecha_registro_hotel")
            if isinstance(fecha_base, datetime):
                fecha_base = fecha_base.date()
            if not isinstance(fecha_base, date):
                continue

            dias_sin_carga = (hoy - fecha_base).days
            if dias_sin_carga < ALERT_HOTEL_INACTIVITY_DAYS:
                continue

            hotel_id = hotel.get("id")
            fecha_base_iso = _fecha_iso(fecha_base)
            alertas_vigentes.add((str(hotel_id), fecha_base_iso))

            if hotel.get("fecha_ultima_carga"):
                resumen = (
                    f"El hotel no registra cargas desde hace {dias_sin_carga} días. "
                    f"Última carga detectada el {fecha_base.strftime('%d/%m/%Y')}."
                )
            else:
                resumen = (
                    f"El hotel no registra cargas desde su alta en el sistema y acumula "
                    f"{dias_sin_carga} días sin movimientos."
                )

            payload = {
                "hotel_id": hotel_id,
                "dias_sin_carga": dias_sin_carga,
                "fecha_ultima_carga": fecha_base_iso,
                "sin_cargas_desde_alta": not bool(hotel.get("fecha_ultima_carga")),
                "umbral_dias": ALERT_HOTEL_INACTIVITY_DAYS,
            }

            cursor.execute(
                """
                INSERT INTO alertas_sistema (
                    tipo, severidad, estado, bloqueante, sujeto_nombre, sujeto_documento,
                    hotel_origen, hotel_relacionado, huesped_id, huesped_relacionado_id,
                    fecha_entrada, fecha_salida, horas_lapso, resumen, payload_json,
                    importacion_tipo, usuario_creacion_id
                )
                SELECT
                    %s, %s, 'pendiente', %s, %s, NULL,
                    %s, NULL, NULL, NULL,
                    %s, NULL, %s, %s, %s,
                    %s, NULL
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM alertas_sistema
                    WHERE tipo = %s
                      AND COALESCE(payload_json, '') <> ''
                      AND payload_json::jsonb ->> 'hotel_id' = %s
                      AND payload_json::jsonb ->> 'fecha_ultima_carga' = %s
                )
                """,
                (
                    ALERTA_HOTEL_SIN_CARGAS,
                    ALERT_TYPE_SETTINGS.get(ALERTA_HOTEL_SIN_CARGAS, {}).get("severidad", "warning"),
                    ALERT_TYPE_SETTINGS.get(ALERTA_HOTEL_SIN_CARGAS, {}).get("bloqueante", False),
                    hotel.get("nombre") or "Hotel sin nombre",
                    hotel.get("nombre") or "Hotel sin nombre",
                    fecha_base,
                    dias_sin_carga * 24,
                    resumen,
                    _serializar_payload(payload),
                    "monitoreo",
                    ALERTA_HOTEL_SIN_CARGAS,
                    str(hotel_id),
                    fecha_base_iso,
                ),
            )
            alertas_creadas += max(cursor.rowcount or 0, 0)

        cursor.execute(
            """
            SELECT id, payload_json
            FROM alertas_sistema
            WHERE tipo = %s
              AND estado IN ('pendiente', 'revisada')
            """,
            (ALERTA_HOTEL_SIN_CARGAS,),
        )

        for alerta in cursor.fetchall() or []:
            payload = _deserializar_payload(alerta.get("payload_json"))
            clave = (
                str(payload.get("hotel_id") or ""),
                str(payload.get("fecha_ultima_carga") or ""),
            )
            if clave in alertas_vigentes:
                continue

            cursor.execute(
                """
                UPDATE alertas_sistema
                SET estado = 'confirmada',
                    fecha_revision = CURRENT_TIMESTAMP,
                    usuario_revision_id = NULL
                WHERE id = %s
                """,
                (alerta.get("id"),),
            )
            alertas_cerradas += max(cursor.rowcount or 0, 0)

        conn.commit()
        resultado.update(
            {
                "vigentes": len(alertas_vigentes),
                "creadas": alertas_creadas,
                "cerradas": alertas_cerradas,
            }
        )
    except Exception:
        conn.rollback()
    finally:
        cursor.close()
        db.liberar_conexion(conn)

    return resultado


def evaluar_huesped_importacion(
    conn,
    huesped: dict,
    hotel_id: int | None = None,
    hotel_nombre: str = "",
    estado_lote: dict | None = None,
) -> dict:
    estado_lote = estado_lote or _crear_estado_lote()
    hotel_ref = hotel_nombre or (f"hotel:{hotel_id}" if hotel_id else "sin-hotel")
    alertas = []
    alertas.extend(_alertas_lote(huesped, hotel_ref, estado_lote))
    alertas.extend(_buscar_duplicados_existentes(conn, huesped, hotel_id, hotel_nombre or hotel_ref))
    alertas = _deduplicar_alertas(alertas)

    _registrar_en_lote(estado_lote, huesped, hotel_ref)

    bloqueante = any(alerta.get("bloqueante") for alerta in alertas)
    tiene_alertas = bool(alertas)
    return {
        "estado": "blocked" if bloqueante else "warning" if tiene_alertas else "clean",
        "bloqueante": bloqueante,
        "total": len(alertas),
        "alertas": alertas,
    }


def analizar_preview_importacion(huespedes: list, hotel_resolver) -> tuple[list, dict]:
    estado_lote = _crear_estado_lote()
    resumen = {
        "bloqueadas": 0,
        "advertencias": 0,
        "sin_alertas": 0,
        "alertas_totales": 0,
    }
    enriquecidos = []

    conn = db.obtener_conexion()
    if not conn:
        for huesped in huespedes:
            copia = dict(huesped)
            copia["alert_evaluacion"] = {"estado": "clean", "bloqueante": False, "total": 0, "alertas": []}
            enriquecidos.append(copia)
        resumen["sin_alertas"] = len(huespedes)
        return enriquecidos, resumen

    try:
        for huesped in huespedes:
            hotel_id, hotel_nombre = hotel_resolver(conn, huesped)
            evaluacion = evaluar_huesped_importacion(
                conn,
                huesped,
                hotel_id=hotel_id,
                hotel_nombre=hotel_nombre,
                estado_lote=estado_lote,
            )
            copia = dict(huesped)
            copia["alert_evaluacion"] = evaluacion
            enriquecidos.append(copia)

            resumen["alertas_totales"] += evaluacion["total"]
            if evaluacion["estado"] == "blocked":
                resumen["bloqueadas"] += 1
            elif evaluacion["estado"] == "warning":
                resumen["advertencias"] += 1
            else:
                resumen["sin_alertas"] += 1
    finally:
        db.liberar_conexion(conn)

    return enriquecidos, resumen


def crear_alertas_desde_evaluacion(
    cursor,
    huesped: dict,
    evaluacion: dict,
    usuario_id: int,
    importacion_tipo: str,
    hotel_origen: str,
    huesped_id: int | None = None,
) -> int:
    creadas = 0
    for alerta in evaluacion.get("alertas", []):
        payload = {
            "huesped": {
                "apellido_nombre": huesped.get("apellido_nombre"),
                "dni_pasaporte": huesped.get("dni_pasaporte"),
                "telefono": huesped.get("telefono"),
                "fecha_entrada": huesped.get("fecha_entrada"),
                "fecha_salida": huesped.get("fecha_salida"),
            },
            "alerta": alerta,
        }
        cursor.execute(
            """
            INSERT INTO alertas_sistema (
                tipo, severidad, estado, bloqueante, sujeto_nombre, sujeto_documento,
                hotel_origen, hotel_relacionado, huesped_id, huesped_relacionado_id,
                fecha_entrada, fecha_salida, horas_lapso, resumen, payload_json,
                importacion_tipo, usuario_creacion_id
            ) VALUES (%s, %s, 'pendiente', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                alerta.get("tipo"),
                alerta.get("severidad", "warning"),
                alerta.get("bloqueante", False),
                huesped.get("apellido_nombre") or "Sin nombre",
                huesped.get("dni_pasaporte") or None,
                hotel_origen or None,
                alerta.get("hotel_relacionado") or None,
                huesped_id,
                alerta.get("huesped_relacionado_id"),
                huesped.get("fecha_entrada"),
                huesped.get("fecha_salida"),
                alerta.get("horas_lapso"),
                alerta.get("resumen") or "Alerta operativa",
                _serializar_payload(payload),
                importacion_tipo,
                usuario_id,
            ),
        )
        creadas += 1
    return creadas


def contar_alertas_pendientes(sincronizar: bool = True) -> int:
    if sincronizar:
        sincronizar_alertas_hoteles_inactivos()

    fila = db.ejecutar_query_one(
        "SELECT COUNT(*) AS total FROM alertas_sistema WHERE estado = 'pendiente'"
    )
    return int(fila["total"]) if fila else 0


def listar_alertas(
    limit: int = 100,
    estado: str = "",
    severidad: str = "",
    tipo: str = "",
    sincronizar: bool = True,
) -> list:
    if sincronizar:
        sincronizar_alertas_hoteles_inactivos()

    query = """
        SELECT id, tipo, severidad, estado, bloqueante, sujeto_nombre, sujeto_documento,
               hotel_origen, hotel_relacionado, fecha_entrada, fecha_salida, horas_lapso,
               resumen, importacion_tipo, fecha_creacion, fecha_revision, payload_json
        FROM alertas_sistema
        WHERE 1 = 1
    """
    params = []
    if estado:
        query += " AND estado = %s"
        params.append(estado)
    if severidad:
        query += " AND severidad = %s"
        params.append(severidad)
    if tipo:
        query += " AND tipo = %s"
        params.append(tipo)
    query += " ORDER BY CASE estado WHEN 'pendiente' THEN 0 ELSE 1 END, fecha_creacion DESC LIMIT %s"
    params.append(limit)
    resultado = db.ejecutar_query(query, tuple(params), fetch=True) or []
    alertas = []
    for fila in resultado:
        alerta = dict(fila)
        payload = _deserializar_payload(alerta.get("payload_json"))
        alerta.update(
            {
                "tipo_label": ALERT_TYPE_SETTINGS.get(alerta["tipo"], {}).get("label", alerta["tipo"]),
                "dias_sin_carga": payload.get("dias_sin_carga"),
                "fecha_ultima_carga": _fecha_desde_payload(payload.get("fecha_ultima_carga")),
            }
        )
        alertas.append(alerta)
    return alertas


def actualizar_estado_alerta(alerta_id: int, estado: str, usuario_id: int) -> bool:
    if estado not in {"pendiente", "revisada", "descartada", "confirmada"}:
        return False
    actualizado = db.ejecutar_query(
        """
        UPDATE alertas_sistema
        SET estado = %s,
            usuario_revision_id = %s,
            fecha_revision = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        (estado, usuario_id, alerta_id),
        fetch=False,
    )
    return bool(actualizado)


def obtener_configuracion_alertas() -> dict:
    tipos = []
    for tipo in ALERT_ENABLED_TYPES:
        config_tipo = ALERT_TYPE_SETTINGS.get(tipo, {})
        tipos.append(
            {
                "key": tipo,
                "label": config_tipo.get("label", tipo),
                "severidad": config_tipo.get("severidad", "warning"),
                "bloqueante": config_tipo.get("bloqueante", False),
            }
        )

    return {
        "window_hours": ALERT_WINDOW_HOURS,
        "hotel_inactivity_days": ALERT_HOTEL_INACTIVITY_DAYS,
        "types": tipos,
    }


def obtener_metricas_alertas(sincronizar: bool = True) -> dict:
    if sincronizar:
        sincronizar_alertas_hoteles_inactivos()

    resumen = db.ejecutar_query_one(
        """
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE estado = 'pendiente') AS pendientes,
            COUNT(*) FILTER (WHERE estado = 'pendiente' AND severidad IN ('danger', 'critical')) AS pendientes_prioritarios,
            COUNT(*) FILTER (WHERE bloqueante = TRUE AND estado = 'pendiente') AS bloqueantes_pendientes,
            COUNT(*) FILTER (WHERE estado = 'pendiente' AND tipo = %s) AS hoteles_inactivos_pendientes,
            COUNT(*) FILTER (WHERE fecha_creacion >= CURRENT_TIMESTAMP - INTERVAL '24 hours') AS ultimas_24h
        FROM alertas_sistema
        """
        ,
        (ALERTA_HOTEL_SIN_CARGAS,),
    ) or {
        "total": 0,
        "pendientes": 0,
        "pendientes_prioritarios": 0,
        "bloqueantes_pendientes": 0,
        "hoteles_inactivos_pendientes": 0,
        "ultimas_24h": 0,
    }

    por_tipo = db.ejecutar_query(
        """
        SELECT tipo,
               COUNT(*) AS total,
               COUNT(*) FILTER (WHERE estado = 'pendiente') AS pendientes
        FROM alertas_sistema
        GROUP BY tipo
        ORDER BY pendientes DESC, total DESC
        LIMIT 6
        """,
        fetch=True,
    ) or []

    por_severidad = db.ejecutar_query(
        """
        SELECT severidad,
               COUNT(*) AS total,
               COUNT(*) FILTER (WHERE estado = 'pendiente') AS pendientes
        FROM alertas_sistema
        GROUP BY severidad
        ORDER BY total DESC
        """,
        fetch=True,
    ) or []

    recientes = db.ejecutar_query(
        """
        SELECT id, sujeto_nombre, resumen, severidad, estado, fecha_creacion, tipo
        FROM alertas_sistema
        ORDER BY CASE estado WHEN 'pendiente' THEN 0 ELSE 1 END, fecha_creacion DESC
        LIMIT 5
        """,
        fetch=True,
    ) or []

    tipos_config = ALERT_TYPE_SETTINGS
    return {
        "resumen": {
            **dict(resumen),
            "hotel_inactivity_days": ALERT_HOTEL_INACTIVITY_DAYS,
        },
        "por_tipo": [
            {
                **dict(fila),
                "label": tipos_config.get(fila["tipo"], {}).get("label", fila["tipo"]),
            }
            for fila in por_tipo
        ],
        "por_severidad": [dict(fila) for fila in por_severidad],
        "recientes": [
            {
                **dict(fila),
                "tipo_label": tipos_config.get(fila["tipo"], {}).get("label", fila["tipo"]),
            }
            for fila in recientes
        ],
    }