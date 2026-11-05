"""Conexión a la base de Supabase usando la URL del archivo .env de la raíz."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")


def conectar() -> psycopg.Connection:
    url = os.environ.get("SUPABASE_DB_URL", "")
    if not url or "pega-aqui" in url or "[YOUR-PASSWORD]" in url:
        raise SystemExit(
            "Falta SUPABASE_DB_URL en el archivo .env (con la contraseña de la base ya puesta)."
        )
    # prepare_threshold=None: el pooler de Supabase no admite sentencias preparadas.
    # keepalives: evitan que la red corte la conexión si queda un rato sin tráfico
    return psycopg.connect(url, prepare_threshold=None, connect_timeout=20,
                           keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5)


def iniciar_ejecucion(conn: psycopg.Connection, paso: str) -> int:
    # Una ejecución que quedó "en curso" es porque se cortó a la mitad.
    conn.execute(
        "update ejecuciones set estado = 'error', terminada_en = now(), "
        "resumen = '{\"error\": \"interrumpida\"}' where paso = %s and estado = 'en_curso'",
        (paso,),
    )
    fila = conn.execute(
        "insert into ejecuciones (paso) values (%s) returning id", (paso,)
    ).fetchone()
    conn.commit()
    return fila[0]


def terminar_ejecucion(conn: psycopg.Connection, ejecucion_id: int, estado: str, resumen: dict) -> None:
    from psycopg.types.json import Jsonb

    conn.execute(
        "update ejecuciones set terminada_en = now(), estado = %s, resumen = %s where id = %s",
        (estado, Jsonb(resumen), ejecucion_id),
    )
    conn.commit()


def ultima_ejecucion_ok(conn: psycopg.Connection, paso: str):
    """Fecha y resumen de la última ejecución exitosa de un paso (o None)."""
    fila = conn.execute(
        "select terminada_en, resumen from ejecuciones where paso = %s and estado = 'ok' "
        "order by id desc limit 1",
        (paso,),
    ).fetchone()
    conn.commit()  # no dejar una transacción abierta mientras se espera a Wikidata
    return fila
