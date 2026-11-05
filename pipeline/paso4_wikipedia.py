"""Paso 4: carrera y palmarés de los jugadores más relevantes, desde Wikipedia en inglés.

- Toma los N jugadores más visitados en Wikipedia (por defecto 500; ver paso 7).
- De cada artículo lee la ficha (partidos y goles por club y selección, y la fecha
  "al día" que indica el artículo) y el palmarés (títulos y premios por edición).
- Solo vuelve a procesar un jugador si su artículo cambió desde la última vez
  (se compara el número de revisión), así actualizar es rápido.
- Marca como relevantes las competiciones y premios que usan los juegos.

Contenido de Wikipedia: licencia CC BY-SA 4.0 (hay que dar crédito al mostrarlo).
Uso: pipeline/.venv/bin/python pipeline/paso4_wikipedia.py [--cantidad 500] [--forzar]
"""

from __future__ import annotations

import argparse
import re
import sys
import time

import wikidata as wd
import wikipedia as wp
from db import conectar, iniciar_ejecucion, terminar_ejecucion, ultima_ejecucion_ok

PASO = "paso4_wikipedia"

# Artículos (Wikipedia en inglés) de las competiciones y premios que usan los juegos.
# Los títulos son de Wikipedia; los códigos se obtienen de ella al correr.
RELEVANTES = {
    "UEFA Champions League": "torneo_clubes",
    "European Cup": "torneo_clubes",            # nombre de la Champions antes de 1992
    "FIFA World Cup": "torneo_selecciones",
    "UEFA European Championship": "torneo_selecciones",
    "Copa América": "torneo_selecciones",
    "Ballon d'Or": "premio",
    "FIFA Ballon d'Or": "premio",
    "European Golden Shoe": "premio",
    "FIFA Puskás Award": "premio",
    "The Best FIFA Men's Player": "premio",
    "FIFA World Player of the Year": "premio",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def anio_de(texto: str) -> int | None:
    """'2005–06' -> 2006, '2014' -> 2014, '1999–2000' -> 2000."""
    m = re.search(r"(1[89]\d\d|20\d\d)\s*[–/-]\s*(\d{2,4})\b", texto)
    if m:
        ini, fin = int(m.group(1)), m.group(2)
        return int(fin) if len(fin) == 4 else (ini // 100) * 100 + int(fin) + (100 if int(fin) < ini % 100 else 0)
    m = re.search(r"\b(1[89]\d\d|20\d\d)\b", texto)
    return int(m.group(1)) if m else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cantidad", type=int, default=500)
    ap.add_argument("--forzar", action="store_true", help="reprocesar aunque el artículo no haya cambiado")
    args = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)

    with conectar() as conn:
        ejecucion = iniciar_ejecucion(conn, PASO)
        try:
            resumen = correr(conn, ejecucion, args.cantidad, args.forzar)
        except Exception as e:
            conn.rollback()
            terminar_ejecucion(conn, ejecucion, "error", {"error": str(e)[:500]})
            raise
        terminar_ejecucion(conn, ejecucion, "ok", resumen)
    imprimir_reporte(resumen)


def correr(conn, ejecucion, cantidad: int, forzar: bool) -> dict:
    anterior = ultima_ejecucion_ok(conn, PASO)
    inicio = time.time()
    top = [r[0] for r in conn.execute(
        "select qid from jugadores_final order by visitas desc nulls last, popularidad desc, qid limit %s", (cantidad,))]
    revisiones = dict(conn.execute("select jugador_qid, revision from jugadores_wikipedia").fetchall())
    conn.commit()
    log(f"{len(top)} jugadores más relevantes. Buscando sus artículos en Wikipedia en inglés…")

    # Título del artículo en inglés de cada jugador (desde Wikidata)
    titulo_de: dict[str, str] = {}
    for e in wd.entidades(top, props="sitelinks", idiomas="en"):
        t = e.get("sitelinks", {}).get("enwiki", {}).get("title")
        if t:
            titulo_de[e["id"]] = t
    jugador_de = {t: q for q, t in titulo_de.items()}
    sin_articulo = [q for q in top if q not in titulo_de]

    log(f"Leyendo {len(titulo_de)} artículos…")
    leidos = []
    for a in wp.articulos(list(titulo_de.values())):
        q = jugador_de.get(a["titulo_pedido"]) or jugador_de.get(a["titulo"])
        if q:
            leidos.append((q, a))
    log(f"  {len(leidos)} artículos leídos")

    cambiados = [(q, a) for q, a in leidos if forzar or revisiones.get(q) != a["revision"]]
    log(f"  {len(cambiados)} cambiaron desde la última vez (se vuelven a procesar)")

    procesados, sin_ficha = [], []
    enlaces: set[str] = set(RELEVANTES)
    for q, a in cambiados:
        f = wp.ficha(a["texto"])
        h = wp.palmares(a["texto"])
        if not f:
            sin_ficha.append(q)
        procesados.append((q, a, f, h))
        if f:
            enlaces |= {c["equipo_titulo"] for c in f["clubes"] + f["selecciones"] if c["equipo_titulo"]}
        for t in h:
            enlaces.add(t["competicion_titulo"])
            enlaces |= {e[0] for e in t["ediciones"]}

    log(f"Buscando en Wikidata los códigos de {len(enlaces)} artículos enlazados…")
    qid_de = wp.qids_de_titulos(enlaces)

    # Competiciones que aparecen en los palmarés
    comp_tit = {t["competicion_titulo"] for _, _, _, h in procesados for t in h} | set(RELEVANTES)
    comp_qids = {qid_de[t]: t for t in comp_tit if t in qid_de}
    # Si un código tiene varios títulos (p. ej. "Ballon d'Or" y "Ballon d’Or"), se usa el de RELEVANTES
    for t in RELEVANTES:
        if t in qid_de:
            comp_qids[qid_de[t]] = t
    nombres = {e["id"]: wd.etiqueta(e) or comp_qids[e["id"]] for e in
               wd.entidades(list(comp_qids), props="labels", idiomas="es|en")}

    log("Guardando en Supabase…")
    cur = conn.cursor()
    conteo_relevantes: dict[str, int] = {}
    with conn.transaction():
        cur.executemany(
            """insert into competiciones (qid, nombre, articulo_en, relevante, tipo) values (%s, %s, %s, %s, %s)
               on conflict (qid) do update set nombre = excluded.nombre, articulo_en = excluded.articulo_en,
                 relevante = excluded.relevante, tipo = excluded.tipo,
                 actualizado_en = case when (competiciones.nombre, competiciones.relevante, competiciones.tipo)
                   is distinct from (excluded.nombre, excluded.relevante, excluded.tipo)
                   then now() else competiciones.actualizado_en end""",
            [(q, nombres.get(q, t), t, t in RELEVANTES, RELEVANTES.get(t, "otro")) for q, t in comp_qids.items()],
        )
        tipo_rel = {qid_de[t]: tp for t, tp in RELEVANTES.items() if t in qid_de}

        for q, a, f, h in procesados:
            cur.execute(
                """insert into jugadores_wikipedia (jugador_qid, articulo, revision, fecha_revision,
                     al_dia_clubes, al_dia_seleccion) values (%s, %s, %s, %s, %s, %s)
                   on conflict (jugador_qid) do update set articulo = excluded.articulo,
                     revision = excluded.revision, fecha_revision = excluded.fecha_revision,
                     al_dia_clubes = excluded.al_dia_clubes, al_dia_seleccion = excluded.al_dia_seleccion,
                     actualizado_en = now()""",
                (q, a["titulo"], a["revision"], a["fecha_revision"],
                 f["al_dia_clubes"] if f else None, f["al_dia_seleccion"] if f else None),
            )
            # Se reemplaza todo lo del jugador con la versión nueva del artículo
            cur.execute("delete from carrera_wikipedia where jugador_qid = %s", (q,))
            cur.execute("delete from titulos_jugador where jugador_qid = %s and fuente = 'wikipedia_en'", (q,))
            if f:
                cur.executemany(
                    """insert into carrera_wikipedia (jugador_qid, seleccion, orden, equipo_qid, equipo_texto, prestamo,
                         desde, hasta, partidos, goles) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    [(q, c["seleccion"], c["orden"], qid_de.get(c["equipo_titulo"] or ""), c["equipo_texto"] or "?",
                      c["prestamo"], c["desde"], c["hasta"], c["partidos"], c["goles"])
                     for c in f["clubes"] + f["selecciones"]],
                )
            filas = {}
            for t in h:
                comp_q = qid_de.get(t["competicion_titulo"])
                # En premios individuales con enlace genérico ("FIFA World Cup awards") se guarda el nombre visible
                texto = t["competicion_etiqueta"] if t["individual"] else t["competicion_titulo"]
                tipo = tipo_rel.get(comp_q)
                # Un torneo de equipos solo cuenta como título si NO está en la sección "Individual"
                if tipo in ("torneo_clubes", "torneo_selecciones") and t["individual"]:
                    tipo = None
                ediciones = t["ediciones"] or [(None, x) for x in t["anios"]]
                for ed_titulo, etiqueta in ediciones:
                    ed_q = qid_de.get(ed_titulo) if ed_titulo else None
                    anio = anio_de(etiqueta) or anio_de(ed_titulo or "")
                    clave = f"{q}|{comp_q or texto}|{ed_q or etiqueta}"
                    filas[clave] = (clave, q, comp_q, texto, ed_q, etiqueta, anio, t["grupo"],
                                    t["individual"], a["revision"])
                    if tipo:
                        conteo_relevantes[nombres.get(comp_q, texto)] = conteo_relevantes.get(
                            nombres.get(comp_q, texto), 0) + 1
            cur.executemany(
                """insert into titulos_jugador (id, jugador_qid, competicion_qid, competicion_texto, edicion_qid,
                     temporada, anio, grupo, individual, revision) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                list(filas.values()),
            )

    totales = dict(conn.execute(
        """select c.nombre, count(*) from titulos_jugador t join competiciones c on c.qid = t.competicion_qid
           where c.relevante and (c.tipo = 'premio' or not t.individual) group by c.nombre order by 2 desc""").fetchall())
    conn.commit()
    return {
        "jugadores": len(top),
        "con_articulo": len(titulo_de),
        "sin_articulo_en_ingles": len(sin_articulo),
        "procesados": len(procesados),
        "sin_ficha": len(sin_ficha),
        "titulos_relevantes_en_la_base": totales,
        "minutos": round((time.time() - inicio) / 60, 1),
        "anterior": anterior[0].isoformat() if anterior else None,
    }


def imprimir_reporte(r: dict) -> None:
    log("\n=== Reporte del paso 4: Wikipedia ===")
    log(f"Jugadores más relevantes: {r['jugadores']} | con artículo en inglés: {r['con_articulo']} | "
        f"sin artículo: {r['sin_articulo_en_ingles']}")
    log(f"Artículos procesados (nuevos o cambiados): {r['procesados']} | sin ficha de futbolista: {r['sin_ficha']}")
    log("Títulos y premios relevantes guardados:")
    for nombre, n in r["titulos_relevantes_en_la_base"].items():
        log(f"  {nombre:<45} {n}")
    log(f"Tiempo: {r['minutos']} min")


if __name__ == "__main__":
    main()
