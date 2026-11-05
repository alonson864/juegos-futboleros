"""Paso 2: jugadores que pasaron por los clubes de las ligas configuradas.

- Busca en Wikidata a las personas con "miembro del equipo" (P54) en alguno de los
  clubes guardados en el paso 1 (o en sus fichas de "primer equipo").
- Se queda con las que tienen artículo en al menos UMBRAL_WIKIPEDIAS Wikipedias.
- Guarda nombre, nacimiento, nacionalidades, posiciones, popularidad y todos sus
  pasos por clubes y selecciones (con fechas, partidos y goles si Wikidata los tiene).
- Los equipos que no son de nuestras ligas (otros clubes, selecciones, juveniles) se
  guardan en "clubes" con su tipo, deducido de cómo los clasifica Wikidata.
- La foto (P18) solo se anota; el paso 3 baja autor y licencia desde Commons.

Se puede correr muchas veces sin duplicar nada.
Uso: pipeline/.venv/bin/python pipeline/paso2_jugadores.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

from psycopg.types.json import Jsonb

import wikidata as wd
from db import conectar, iniciar_ejecucion, terminar_ejecucion, ultima_ejecucion_ok

PASO = "paso2_jugadores"
UMBRAL_WIKIPEDIAS = 10
HUMANO = "Q5"

# Mismos tipos de club que en el paso 1
TIPOS_CLUB = {
    "Q476028", "Q847017", "Q20639856", "Q103229495", "Q15944511",
    "Q13580678", "Q15896028", "Q94579592",
}

# Palabras que aparecen en los nombres de los tipos de Wikidata (en español o inglés)
_JUVENIL = re.compile(
    r"\b(sub|under|u)[ -]?\d{2}\b|juvenil|youth|reserv|filial|ol[ií]mpic|amateur|"
    r"\bb team\b|equipo b|segundo equipo|academ|cantera|junior",
    re.IGNORECASE,
)
_SELECCION = re.compile(r"selecci[oó]n|national", re.IGNORECASE)
_EQUIPO = re.compile(r"club|team|equipo", re.IGNORECASE)


def log(msg: str) -> None:
    print(msg, flush=True)


# ---------------------------------------------------------------------------
# Lectura desde Wikidata
# ---------------------------------------------------------------------------

def candidatos(clubes: list[str]) -> set[str]:
    """Personas con P54 en esos clubes y al menos UMBRAL sitelinks (filtro grueso)."""
    salida: set[str] = set()
    lote = 15
    for i in range(0, len(clubes), lote):
        valores = " ".join("wd:" + q for q in clubes[i : i + lote])
        filas = wd.sparql(f"""
            SELECT DISTINCT ?j WHERE {{
              VALUES ?club {{ {valores} }}
              # p:/ps: (no wdt:) para incluir TODOS los clubes, no solo el marcado como "preferido"
              ?j p:P54 ?st . ?st ps:P54 ?club .
              FILTER NOT EXISTS {{ ?st wikibase:rank wikibase:DeprecatedRank }}
              ?j wikibase:sitelinks ?s .
              FILTER(?s >= {UMBRAL_WIKIPEDIAS})
              ?j wdt:P31 wd:{HUMANO} .
            }}""")
        salida.update(wd.qid(f["j"]) for f in filas)
        log(f"  clubes {min(i + lote, len(clubes))}/{len(clubes)}: {len(salida)} candidatos")
    return salida


def fecha_wikidata(valor: dict | None) -> tuple[str | None, int | None]:
    """Convierte un valor de tiempo de Wikidata en ('AAAA-MM-DD', precisión)."""
    if not valor:
        return None, None
    t, precision = valor.get("time", ""), valor.get("precision", 0)
    m = re.match(r"^\+(\d{4})-(\d{2})-(\d{2})", t)
    if not m or precision < 9:
        return None, None
    anio, mes, dia = (int(x) for x in m.groups())
    precision = min(precision, 11)
    if precision < 10 or mes == 0:
        mes, precision = 1, min(precision, 9)
    if precision < 11 or dia == 0:
        dia, precision = 1, min(precision, 10)
    # Wikidata a veces trae fechas imposibles (ej. 31 de junio): se baja la precisión.
    try:
        date(anio, mes, dia)
    except ValueError:
        try:
            date(anio, mes, 1)
            dia, precision = 1, 10
        except ValueError:
            mes, dia, precision = 1, 1, 9
    if anio < 1 or anio > 9999:
        return None, None
    return f"{anio:04d}-{mes:02d}-{dia:02d}", precision


def _valor(snak: dict):
    return snak.get("datavalue", {}).get("value") if snak.get("snaktype") == "value" else None


def _cantidad(calificadores: dict, prop: str) -> int | None:
    for snak in calificadores.get(prop, []):
        v = _valor(snak)
        if isinstance(v, dict) and "amount" in v:
            try:
                return int(float(v["amount"]))
            except ValueError:
                return None
    return None


def _tiempo(calificadores: dict, prop: str) -> tuple[str | None, int | None]:
    for snak in calificadores.get(prop, []):
        f = fecha_wikidata(_valor(snak))
        if f[0]:
            return f
    return None, None


def extraer(e: dict, alias: dict[str, str]) -> dict:
    claims = e.get("claims", {})
    nac, prec = None, None
    for st in claims.get("P569", []):
        if st.get("rank") != "deprecated":
            nac, prec = fecha_wikidata(_valor(st["mainsnak"]))
            if nac:
                break
    pasos = []
    for st in claims.get("P54", []):
        if st.get("rank") == "deprecated":
            continue
        v = _valor(st["mainsnak"])
        if not isinstance(v, dict) or "id" not in v:
            continue
        cal = st.get("qualifiers", {})
        inicio, inicio_p = _tiempo(cal, "P580")
        fin, fin_p = _tiempo(cal, "P582")
        pasos.append({
            "id": st["id"],
            "club": alias.get(v["id"], v["id"]),
            "inicio": inicio, "inicio_p": inicio_p,
            "fin": fin, "fin_p": fin_p,
            "partidos": _cantidad(cal, "P1350"),
            "goles": _cantidad(cal, "P1351"),
        })
    fotos = [v for st in claims.get("P18", []) if st.get("rank") != "deprecated"
             and isinstance(v := _valor(st["mainsnak"]), str)]
    return {
        "qid": e["id"],
        "nombre": wd.nombre_futbolistico(wd.etiqueta(e), e.get("sitelinks", {}).get("enwiki", {}).get("title"))
                  or e["id"],
        "nacimiento": nac,
        "precision": prec,
        "nacionalidades": sorted(set(wd.valores(e, "P27"))),
        "posiciones": sorted(set(wd.valores(e, "P413"))),
        "popularidad": wd.contar_wikipedias(e),
        "foto": fotos[0] if fotos else None,
        "pasos": pasos,
    }


def huella(j: dict) -> str:
    datos = {k: j[k] for k in ("nombre", "nacimiento", "precision", "nacionalidades",
                                "posiciones", "popularidad", "foto")}
    datos["pasos"] = sorted(json.dumps(p, sort_keys=True) for p in j["pasos"])
    return hashlib.sha1(json.dumps(datos, sort_keys=True).encode()).hexdigest()


def info_equipos(qids: list[str]) -> dict[str, dict]:
    """Nombre, tipos y país de equipos (consulta liviana por lotes)."""
    salida: dict[str, dict] = {}
    for i in range(0, len(qids), 300):
        valores = " ".join("wd:" + q for q in qids[i : i + 300])
        for f in wd.sparql(f"""
            SELECT ?x ?es ?en ?tipo ?pais WHERE {{
              VALUES ?x {{ {valores} }}
              OPTIONAL {{ ?x rdfs:label ?es FILTER(LANG(?es) = "es") }}
              OPTIONAL {{ ?x rdfs:label ?en FILTER(LANG(?en) = "en") }}
              OPTIONAL {{ ?x wdt:P31 ?tipo }}
              OPTIONAL {{ ?x wdt:P17 ?pais }}
            }}"""):
            d = salida.setdefault(wd.qid(f["x"]), {"nombre": None, "tipos": set(), "pais": None})
            d["nombre"] = d["nombre"] or f.get("es") or f.get("en")
            if "tipo" in f:
                d["tipos"].add(wd.qid(f["tipo"]))
            if "pais" in f and not d["pais"]:
                d["pais"] = wd.qid(f["pais"])
        log(f"  equipos {min(i + 300, len(qids))}/{len(qids)}")
    return salida


def nombres(qids: set[str]) -> dict[str, str]:
    return {e["id"]: wd.etiqueta(e) or e["id"] for e in wd.entidades(qids, props="labels", idiomas="es|en")}


def clasificar(nombre: str | None, tipos: set[str], nombre_tipo: dict[str, str]) -> str:
    texto = " | ".join([nombre or ""] + [nombre_tipo.get(t, "") for t in tipos])
    textos_tipo = " | ".join(nombre_tipo.get(t, "") for t in tipos)
    es_seleccion = bool(_SELECCION.search(textos_tipo))
    es_juvenil = bool(_JUVENIL.search(texto))
    if es_seleccion:
        return "seleccion_juvenil" if es_juvenil else "seleccion"
    if es_juvenil:
        return "juvenil"
    if tipos & TIPOS_CLUB or _EQUIPO.search(textos_tipo):
        return "club"
    return "desconocido"


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------

COPIA = Path(__file__).resolve().parent / "salida" / "paso2_descarga.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--usar-copia", action="store_true",
                    help="no bajar de Wikidata: usar la última descarga guardada en pipeline/salida/")
    ap.add_argument("--incremental", action="store_true",
                    help="partir de la última descarga y bajar solo los candidatos nuevos")
    args = ap.parse_args()
    # La conexión no se deja abierta durante la descarga (dura mucho y se corta):
    # se abre una para leer lo necesario y otra nueva para guardar.
    with conectar() as conn:
        ejecucion = iniciar_ejecucion(conn, PASO)
        anterior = ultima_ejecucion_ok(conn, PASO)
        clubes_liga = [r[0] for r in conn.execute(
            "select distinct c.qid from clubes_final c join clubes_ligas l on l.club_qid = c.qid order by 1")]
        alias = dict(conn.execute("select qid, club_qid from clubes_alias").fetchall())
        conn.commit()
    try:
        resumen = correr(ejecucion, anterior, clubes_liga, alias, args.usar_copia, args.incremental)
    except Exception as e:
        with conectar() as conn:
            terminar_ejecucion(conn, ejecucion, "error", {"error": str(e)[:500]})
        raise
    with conectar() as conn:
        terminar_ejecucion(conn, ejecucion, "ok", resumen)
    imprimir_reporte(resumen)


def correr(ejecucion, anterior, clubes_liga, alias, usar_copia: bool = False, incremental: bool = False) -> dict:
    inicio = time.time()
    if usar_copia:
        log(f"Usando la descarga guardada en {COPIA.name}…")
        d = json.loads(COPIA.read_text(encoding="utf-8"))
        jugadores, nombre_pais, nombre_pos = d["jugadores"], d["paises"], d["posiciones"]
        info = {q: {**x, "tipos": set(x["tipos"])} for q, x in d["equipos"].items()}
        return terminar_correr(ejecucion, anterior, clubes_liga, jugadores, info,
                               nombre_pais, nombre_pos, inicio)
    log(f"Buscando jugadores de {len(clubes_liga)} clubes (+{len(alias)} fichas de equipo)…")
    ids = candidatos(clubes_liga + list(alias))

    # Incremental: se parte de la última descarga y solo se bajan los candidatos que faltan
    jugadores: dict[str, dict] = {}
    previo_info: dict[str, dict] = {}
    previo_pais: dict[str, str] = {}
    previo_pos: dict[str, str] = {}
    if incremental and COPIA.exists():
        d = json.loads(COPIA.read_text(encoding="utf-8"))
        jugadores = {q: j for q, j in d["jugadores"].items() if q in ids}
        previo_info = {q: {**x, "tipos": set(x["tipos"])} for q, x in d["equipos"].items()}
        previo_pais, previo_pos = d["paises"], d["posiciones"]
        # Los alias pueden haber cambiado: se vuelven a aplicar a los pasos guardados
        for j in jugadores.values():
            for paso in j["pasos"]:
                paso["club"] = alias.get(paso["club"], paso["club"])
        ids = ids - set(jugadores)
        log(f"Incremental: {len(jugadores)} jugadores ya descargados; faltan {len(ids)} candidatos")

    log(f"Leyendo las fichas de {len(ids)} candidatos…")
    for n, e in enumerate(wd.entidades(ids, idiomas="es|en|pt|it|fr|de"), 1):
        if HUMANO not in wd.valores(e, "P31"):
            continue
        j = extraer(e, alias)
        if j["popularidad"] >= UMBRAL_WIKIPEDIAS:
            jugadores[j["qid"]] = j
        if n % 500 == 0:
            log(f"  {n}/{len(ids)} fichas leídas, {len(jugadores)} jugadores con {UMBRAL_WIKIPEDIAS}+ Wikipedias")
    log(f"  {len(jugadores)} jugadores con {UMBRAL_WIKIPEDIAS}+ Wikipedias")

    # Equipos nuevos (otros clubes, selecciones, juveniles)
    equipos = {p["club"] for j in jugadores.values() for p in j["pasos"]}
    nuevos_eq = sorted(equipos - set(clubes_liga) - set(previo_info))
    log(f"Clasificando {len(nuevos_eq)} equipos que no son de nuestras ligas…")
    info = info_equipos(nuevos_eq)
    nombre_tipo = nombres({t for d in info.values() for t in d["tipos"]})
    for q, d in info.items():
        d["tipo"] = clasificar(d["nombre"], d["tipos"], nombre_tipo)
    info.update({q: x for q, x in previo_info.items() if q in equipos and q not in clubes_liga})

    # Nombres de países y posiciones
    paises = {j for x in jugadores.values() for j in x["nacionalidades"]} | {
        d["pais"] for d in info.values() if d["pais"]}
    posiciones = {p for x in jugadores.values() for p in x["posiciones"]}
    log(f"Leyendo nombres de {len(paises - set(previo_pais))} países y {len(posiciones - set(previo_pos))} posiciones…")
    nombre_pais = {**{q: n for q, n in previo_pais.items() if q in paises}, **nombres(paises - set(previo_pais))}
    nombre_pos = {**{q: n for q, n in previo_pos.items() if q in posiciones}, **nombres(posiciones - set(previo_pos))}

    # Copia local antes de guardar: si algo falla, se reintenta con --usar-copia
    COPIA.parent.mkdir(exist_ok=True)
    COPIA.write_text(json.dumps({
        "jugadores": jugadores, "paises": nombre_pais, "posiciones": nombre_pos,
        "equipos": {q: {**x, "tipos": sorted(x["tipos"])} for q, x in info.items()},
    }, ensure_ascii=False), encoding="utf-8")
    log(f"Descarga guardada en pipeline/salida/{COPIA.name}")
    return terminar_correr(ejecucion, anterior, clubes_liga, jugadores, info,
                           nombre_pais, nombre_pos, inicio)


def terminar_correr(ejecucion, anterior, clubes_liga, jugadores, info,
                    nombre_pais, nombre_pos, inicio) -> dict:
    log("Guardando en Supabase…")
    with conectar() as conn:
        cambios = guardar(conn, ejecucion, jugadores, info, nombre_pais, nombre_pos)

    sin_foto = sum(1 for j in jugadores.values() if not j["foto"])
    sin_nac = sum(1 for j in jugadores.values() if not j["nacimiento"] or (j["precision"] or 0) < 11)
    tipo_eq = {q: d["tipo"] for q, d in info.items()}
    tipo_eq.update({q: "club" for q in clubes_liga})
    pasos_club = [p for j in jugadores.values() for p in j["pasos"] if tipo_eq.get(p["club"]) == "club"]
    jug_fechas_inc = sum(
        1 for j in jugadores.values()
        if any(tipo_eq.get(p["club"]) == "club" and not p["inicio"] for p in j["pasos"])
    )
    por_tipo: dict[str, int] = {}
    for d in info.values():
        por_tipo[d["tipo"]] = por_tipo.get(d["tipo"], 0) + 1
    return {
        "jugadores": len(jugadores),
        "sin_foto": sin_foto,
        "sin_nacimiento_exacto": sin_nac,
        "jugadores_con_pasos_sin_fecha": jug_fechas_inc,
        "pasos_por_clubes": len(pasos_club),
        "pasos_por_clubes_sin_inicio": sum(1 for p in pasos_club if not p["inicio"]),
        "equipos_nuevos_por_tipo": por_tipo,
        "cambios": cambios,
        "minutos": round((time.time() - inicio) / 60, 1),
        "anterior": anterior[0].isoformat() if anterior else None,
    }


def guardar(conn, ejecucion, jugadores, info, nombre_pais, nombre_pos) -> dict:
    antes = dict(conn.execute("select qid, huella from jugadores").fetchall())
    ahora = {q: huella(j) for q, j in jugadores.items()}
    cambios = {
        "nuevos": sorted(set(ahora) - set(antes)),
        "modificados": sorted(q for q in set(ahora) & set(antes) if ahora[q] != antes[q]),
        "eliminados": sorted(set(antes) - set(ahora)),
    }
    cur = conn.cursor()
    with conn.transaction():
        cur.executemany(
            """insert into paises (qid, nombre) values (%s, %s)
               on conflict (qid) do update set nombre = excluded.nombre, actualizado_en = now()
               where paises.nombre is distinct from excluded.nombre""",
            list(nombre_pais.items()),
        )
        cur.executemany(
            """insert into posiciones (qid, nombre) values (%s, %s)
               on conflict (qid) do update set nombre = excluded.nombre, actualizado_en = now()
               where posiciones.nombre is distinct from excluded.nombre""",
            list(nombre_pos.items()),
        )
        cur.executemany(
            """insert into clubes (qid, nombre, pais_qid, tipo, ultima_ejecucion) values (%s, %s, %s, %s, %s)
               on conflict (qid) do update set nombre = excluded.nombre, pais_qid = excluded.pais_qid,
                 tipo = excluded.tipo, ultima_ejecucion = excluded.ultima_ejecucion,
                 actualizado_en = case when (clubes.nombre, clubes.pais_qid, clubes.tipo)
                   is distinct from (excluded.nombre, excluded.pais_qid, excluded.tipo)
                   then now() else clubes.actualizado_en end""",
            [(q, d["nombre"] or q, d["pais"] if d["pais"] in nombre_pais else None, d["tipo"], ejecucion)
             for q, d in info.items()],
        )
        # Equipos sin ninguna ficha legible en Wikidata: se guardan igual para no perder el paso.
        faltan = {p["club"] for j in jugadores.values() for p in j["pasos"]} - set(info) - {
            r[0] for r in conn.execute("select qid from clubes")}
        cur.executemany(
            "insert into clubes (qid, nombre, tipo, ultima_ejecucion) values (%s, %s, 'desconocido', %s) "
            "on conflict do nothing",
            [(q, q, ejecucion) for q in faltan],
        )

        cur.executemany(
            """insert into jugadores (qid, nombre, fecha_nacimiento, precision_nacimiento, nacionalidades,
                 posiciones, popularidad, huella, ultima_ejecucion)
               values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               on conflict (qid) do update set nombre = excluded.nombre,
                 fecha_nacimiento = excluded.fecha_nacimiento,
                 precision_nacimiento = excluded.precision_nacimiento,
                 nacionalidades = excluded.nacionalidades, posiciones = excluded.posiciones,
                 popularidad = excluded.popularidad, ultima_ejecucion = excluded.ultima_ejecucion,
                 actualizado_en = case when jugadores.huella is distinct from excluded.huella
                   then now() else jugadores.actualizado_en end,
                 huella = excluded.huella""",
            [(q, j["nombre"], j["nacimiento"], j["precision"], j["nacionalidades"], j["posiciones"],
              j["popularidad"], ahora[q], ejecucion) for q, j in jugadores.items()],
        )
        pasos = [(p["id"], q, p["club"], p["inicio"], p["inicio_p"], p["fin"], p["fin_p"],
                  p["partidos"], p["goles"], ejecucion) for q, j in jugadores.items() for p in j["pasos"]]
        cur.executemany(
            """insert into pasos_por_club (id_wikidata, jugador_qid, club_qid, inicio, inicio_precision, fin,
                 fin_precision, partidos, goles, ultima_ejecucion)
               values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               on conflict (id_wikidata) do update set jugador_qid = excluded.jugador_qid,
                 club_qid = excluded.club_qid, inicio = excluded.inicio,
                 inicio_precision = excluded.inicio_precision, fin = excluded.fin,
                 fin_precision = excluded.fin_precision, partidos = excluded.partidos,
                 goles = excluded.goles, ultima_ejecucion = excluded.ultima_ejecucion,
                 actualizado_en = case when (pasos_por_club.club_qid, pasos_por_club.inicio, pasos_por_club.fin,
                   pasos_por_club.partidos, pasos_por_club.goles) is distinct from (excluded.club_qid,
                   excluded.inicio, excluded.fin, excluded.partidos, excluded.goles)
                   then now() else pasos_por_club.actualizado_en end""",
            pasos,
        )
        # Pasos que Wikidata ya no tiene
        conn.execute("delete from pasos_por_club where not (id_wikidata = any(%s))", ([p[0] for p in pasos],))

        # Fotos: se anota el archivo; si cambió, se borran autor y licencia para que el paso 3 los busque
        fotos = [(q, j["foto"], ejecucion) for q, j in jugadores.items() if j["foto"]]
        cur.executemany(
            """insert into imagenes (jugador_qid, archivo, ultima_ejecucion) values (%s, %s, %s)
               on conflict (jugador_qid) do update set archivo = excluded.archivo,
                 ultima_ejecucion = excluded.ultima_ejecucion,
                 url = case when imagenes.archivo = excluded.archivo then imagenes.url end,
                 url_miniatura = case when imagenes.archivo = excluded.archivo then imagenes.url_miniatura end,
                 autor = case when imagenes.archivo = excluded.archivo then imagenes.autor end,
                 licencia = case when imagenes.archivo = excluded.archivo then imagenes.licencia end,
                 licencia_url = case when imagenes.archivo = excluded.archivo then imagenes.licencia_url end,
                 licencia_libre = imagenes.archivo = excluded.archivo and imagenes.licencia_libre,
                 actualizado_en = case when imagenes.archivo = excluded.archivo
                   then imagenes.actualizado_en else now() end""",
            fotos,
        )
        conn.execute("delete from imagenes where not (jugador_qid = any(%s))", ([f[0] for f in fotos],))

        # Jugadores que ya no cumplen el filtro
        conn.execute("delete from jugadores where qid = any(%s)", (cambios["eliminados"],))

        registro = [(ejecucion, "jugadores", q, tipo, Jsonb({"nombre": jugadores[q]["nombre"]})
                     if q in jugadores else None)
                    for tipo, lista in (("nuevo", cambios["nuevos"]), ("modificado", cambios["modificados"]),
                                        ("eliminado", cambios["eliminados"]))
                    for q in lista]
        cur.executemany(
            "insert into cambios (ejecucion_id, tabla, registro, tipo, detalle) values (%s, %s, %s, %s, %s)",
            registro,
        )
    return {k: len(v) for k, v in cambios.items()}


def imprimir_reporte(r: dict) -> None:
    log("\n=== Reporte del paso 2: jugadores ===")
    log(f"Jugadores ({UMBRAL_WIKIPEDIAS}+ Wikipedias):            {r['jugadores']}")
    log(f"Sin foto en Wikidata:                     {r['sin_foto']}")
    log(f"Sin fecha de nacimiento exacta:           {r['sin_nacimiento_exacto']}")
    log(f"Con algún paso por club sin fecha inicio: {r['jugadores_con_pasos_sin_fecha']}")
    log(f"Pasos por clubes: {r['pasos_por_clubes']} ({r['pasos_por_clubes_sin_inicio']} sin fecha de inicio)")
    log(f"Equipos nuevos por tipo: {r['equipos_nuevos_por_tipo']}")
    c = r["cambios"]
    desde = f"desde el {r['anterior'][:16].replace('T', ' ')}" if r["anterior"] else "(primera ejecución)"
    log(f"Cambios {desde}: {c['nuevos']} nuevos, {c['modificados']} modificados, {c['eliminados']} eliminados.")
    log(f"Tiempo: {r['minutos']} min")


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()
