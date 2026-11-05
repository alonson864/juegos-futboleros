"""Paso 1: clubes de las ligas de pipeline/ligas.json.

Junta tres fuentes:
  - "club": en Wikidata, el club dice que juega/jugó en la liga (propiedad P118).
  - "temporadas": en Wikidata, el club es participante (P1923) de una temporada de la liga.
  - "wikipedia": solo para ligas con "wikipedia_temporadas" en ligas.json; clubes del
    mismo país enlazados desde el artículo de cada temporada en Wikipedia en español
    (licencia CC BY-SA).

Guarda ligas, países, clubes y la relación club-liga en Supabase, registra qué
cambió desde la última vez y escribe pipeline/salida/clubes_para_revisar.csv.

Se puede correr muchas veces sin duplicar nada.
Uso: pipeline/.venv/bin/python pipeline/paso1_clubes.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
from pathlib import Path

from psycopg.types.json import Jsonb

import wikidata as wd
from db import conectar, iniciar_ejecucion, terminar_ejecucion, ultima_ejecucion_ok

AQUI = Path(__file__).resolve().parent
PASO = "paso1_clubes"

# Tipos de Wikidata (P31) que aceptamos como club. Salen de explorar las 7 ligas
# el 2026-11-04 (ver tipos encontrados en el historial del proyecto).
TIPOS_CLUB = {
    "Q476028",     # club de fútbol
    "Q847017",     # club deportivo
    "Q20639856",   # club deportivo profesional
    "Q103229495",  # equipo masculino de fútbol
    "Q15944511",   # equipo de fútbol
    "Q13580678",   # club polideportivo
    "Q15896028",   # equipo deportivo desaparecido
    "Q94579592",   # equipo de fútbol desaparecido
}
HUMANO = "Q5"
EQUIPO_MASCULINO = "Q103229495"  # "primer equipo masculino" de un club (común en Alemania)


def cargar_ligas() -> list[dict]:
    return json.loads((AQUI / "ligas.json").read_text(encoding="utf-8"))["ligas"]


def candidatos(ligas: list[dict]) -> dict[tuple[str, str], dict]:
    """(club, liga) -> {origen, inicio, fin, temporadas} desde las dos fuentes."""
    valores = " ".join("wd:" + l["qid"] for l in ligas)
    pares: dict[tuple[str, str], dict] = {}

    print("Consultando clubes que dicen jugar en cada liga (P118)…")
    t = time.time()
    filas = wd.sparql(f"""
        SELECT ?liga ?club ?ini ?fin WHERE {{
          VALUES ?liga {{ {valores} }}
          ?club p:P118 ?st . ?st ps:P118 ?liga .
          FILTER NOT EXISTS {{ ?club wdt:P31 wd:{HUMANO} }}
          OPTIONAL {{ ?st pq:P580 ?ini }}
          OPTIONAL {{ ?st pq:P582 ?fin }}
        }}""")
    print(f"  {len(filas)} filas en {time.time() - t:.0f}s")
    for f in filas:
        clave = (wd.qid(f["club"]), wd.qid(f["liga"]))
        dato = pares.setdefault(clave, {"origen": set(), "inicio": None, "fin": None, "temporadas": None})
        dato["origen"].add("club")
        dato["inicio"] = min(filter(None, [dato["inicio"], wd.fecha(f.get("ini"))]), default=None)
        dato["fin"] = max(filter(None, [dato["fin"], wd.fecha(f.get("fin"))]), default=None)

    print("Consultando participantes de las temporadas de cada liga (P1923)…")
    t = time.time()
    filas = wd.sparql(f"""
        SELECT ?liga ?club (COUNT(DISTINCT ?temp) AS ?n) (MIN(?ini) AS ?desde) (MAX(?fin) AS ?hasta) WHERE {{
          VALUES ?liga {{ {valores} }}
          ?temp wdt:P3450 ?liga ; wdt:P1923 ?club .
          FILTER NOT EXISTS {{ ?club wdt:P31 wd:{HUMANO} }}
          OPTIONAL {{ ?temp wdt:P580 ?ini }}
          OPTIONAL {{ ?temp wdt:P582 ?fin }}
        }} GROUP BY ?liga ?club""")
    print(f"  {len(filas)} filas en {time.time() - t:.0f}s")
    for f in filas:
        clave = (wd.qid(f["club"]), wd.qid(f["liga"]))
        dato = pares.setdefault(clave, {"origen": set(), "inicio": None, "fin": None, "temporadas": None})
        dato["origen"].add("temporadas")
        dato["temporadas"] = int(f["n"])
        # Si el club no trae fechas propias, usamos la primera y la última temporada.
        dato["inicio"] = dato["inicio"] or wd.fecha(f.get("desde"))
        dato["fin"] = dato["fin"] or wd.fecha(f.get("hasta"))
    return pares


def desde_wikipedia(ligas: list[dict], pares: dict) -> None:
    """Agrega a `pares` los clubes enlazados desde los artículos de temporada en Wikipedia."""
    ligas_wp = [l for l in ligas if l.get("wikipedia_temporadas")]
    if not ligas_wp:
        return
    pais_liga = {e["id"]: (wd.valores(e, "P17") or [None])[0]
                 for e in wd.entidades([l["qid"] for l in ligas_wp], props="claims")}
    for liga in ligas_wp:
        print(f"Leyendo artículos de temporada de {liga['nombre']} en Wikipedia en español…")
        temporadas = wd.sparql(f"""
            SELECT ?art WHERE {{
              ?temp wdt:P3450 wd:{liga["qid"]} .
              ?art schema:about ?temp ; schema:isPartOf <https://es.wikipedia.org/> .
            }}""")
        apariciones: dict[str, list[str]] = {}  # club -> años de las temporadas
        for t in temporadas:
            titulo = requests_unquote(t["art"].rsplit("/", 1)[-1]).replace("_", " ")
            anio = re.search(r"\b(1[89]\d\d|20\d\d)\b", titulo)
            for q in set(wd.enlaces_wikipedia(titulo)):
                apariciones.setdefault(q, []).append(anio.group(1) if anio else "")
        print(f"  {len(temporadas)} artículos, {len(apariciones)} enlaces distintos; filtrando clubes…")

        pais = pais_liga.get(liga["qid"])
        for club, paises in clubes_y_paises(list(apariciones)).items():
            anios = sorted(a for a in apariciones[club] if a)
            # Clubes de otro país (rivales internacionales mencionados) no cuentan.
            # Sin país en Wikidata, se acepta solo si aparece en 2 o más temporadas.
            if paises and pais not in paises:
                continue
            if not paises and len(apariciones[club]) < 2:
                continue
            dato = pares.setdefault((club, liga["qid"]),
                                    {"origen": set(), "inicio": None, "fin": None, "temporadas": None})
            dato["origen"].add("wikipedia")
            dato["temporadas"] = max(dato["temporadas"] or 0, len(apariciones[club]))
            if anios:
                dato["inicio"] = dato["inicio"] or f"{anios[0]}-01-01"
                dato["fin"] = dato["fin"] or f"{anios[-1]}-12-31"


def clubes_y_paises(qids: list[str]) -> dict[str, set[str]]:
    """De una lista de códigos, devuelve solo los que son clubes, con sus países (P17).

    Pregunta por lotes con SPARQL en vez de bajar la ficha completa de cada uno.
    """
    tipos = " ".join("wd:" + t for t in TIPOS_CLUB)
    salida: dict[str, set[str]] = {}
    for i in range(0, len(qids), 400):
        valores = " ".join("wd:" + q for q in qids[i : i + 400])
        for f in wd.sparql(f"""
            SELECT DISTINCT ?x ?pais WHERE {{
              VALUES ?x {{ {valores} }}
              VALUES ?tipo {{ {tipos} }}
              ?x wdt:P31 ?tipo .
              OPTIONAL {{ ?x wdt:P17 ?pais }}
            }}"""):
            paises = salida.setdefault(wd.qid(f["x"]), set())
            if "pais" in f:
                paises.add(wd.qid(f["pais"]))
    return salida


def requests_unquote(texto: str) -> str:
    from urllib.parse import unquote
    return unquote(texto)


def unir_equipos(pares: dict, info: dict, ligas_qid: set[str]) -> dict[str, tuple[str, str]]:
    """Reemplaza las fichas de 'primer equipo' por su club. Devuelve {equipo: (club, motivo)}."""
    equipos = [q for q in {c for c, _ in pares} if EQUIPO_MASCULINO in wd.valores(info.get(q, {}), "P31")]
    alias: dict[str, tuple[str, str]] = {}
    for q in equipos:
        padres = [p for p in wd.valores(info[q], "P361") if p not in ligas_qid]
        if padres:
            alias[q] = (padres[0], "P361")
    faltan = [q for q in equipos if q not in alias]
    if faltan:
        valores = " ".join("wd:" + q for q in faltan)
        for f in wd.sparql(f"SELECT ?equipo ?club WHERE {{ VALUES ?equipo {{ {valores} }} ?club wdt:P527 ?equipo . }}"):
            alias.setdefault(wd.qid(f["equipo"]), (wd.qid(f["club"]), "P527"))

    nuevos = {c for c, _ in alias.values()} - info.keys()
    info.update({e["id"]: e for e in wd.entidades(nuevos)})

    for club, liga in list(pares):
        if club not in alias:
            continue
        dato = pares.pop((club, liga))
        destino = pares.setdefault((alias[club][0], liga),
                                   {"origen": set(), "inicio": None, "fin": None, "temporadas": None})
        destino["origen"] |= dato["origen"]
        destino["inicio"] = min(filter(None, [destino["inicio"], dato["inicio"]]), default=None)
        destino["fin"] = max(filter(None, [destino["fin"], dato["fin"]]), default=None)
        destino["temporadas"] = max(filter(None, [destino["temporadas"], dato["temporadas"]]), default=None)
    print(f"  {len(alias)} fichas de 'primer equipo' unidas a su club "
          f"({len(equipos) - len(alias)} sin club conocido)")
    return alias


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)  # mostrar el avance en vivo
    ligas = cargar_ligas()
    nombre_liga = {l["qid"]: l["nombre"] for l in ligas}

    with conectar() as conn:
        ejecucion = iniciar_ejecucion(conn, PASO)
        try:
            resumen = correr(conn, ligas, nombre_liga, ejecucion)
        except Exception as e:
            conn.rollback()
            terminar_ejecucion(conn, ejecucion, "error", {"error": str(e)[:500]})
            raise
        terminar_ejecucion(conn, ejecucion, "ok", resumen)

    imprimir_reporte(resumen)


def correr(conn, ligas, nombre_liga, ejecucion) -> dict:
    anterior = ultima_ejecucion_ok(conn, PASO)
    pares = candidatos(ligas)
    desde_wikipedia(ligas, pares)

    print(f"Leyendo detalles de {len({c for c, _ in pares})} clubes candidatos…")
    info = {e["id"]: e for e in wd.entidades({c for c, _ in pares})}
    alias = unir_equipos(pares, info, {l["qid"] for l in ligas})
    unidos: dict[str, list[str]] = {}
    for equipo, (club, _) in alias.items():
        unidos.setdefault(club, []).append(equipo)

    desde_liga = {l["qid"]: l["desde"] for l in ligas if l.get("desde")}
    aceptados: dict[str, dict] = {}
    filas_csv = []
    for (club, liga), dato in sorted(pares.items(), key=lambda x: (nombre_liga[x[0][1]], x[0][0])):
        e = info.get(club, {})
        tipos = wd.valores(e, "P31")
        es_club = bool(set(tipos) & TIPOS_CLUB) or "temporadas" in dato["origen"]
        motivo = "" if es_club else "no es de un tipo de club aceptado"
        # Ficha de "primer equipo" sin club conocido y sin ningún artículo: es un
        # duplicado de un club que ya está en la lista con su propia ficha.
        if es_club and EQUIPO_MASCULINO in tipos and wd.contar_wikipedias(e) == 0:
            es_club, motivo = False, "ficha de equipo sin artículo ni club conocido (duplicado)"
        desde = desde_liga.get(liga)
        if es_club and desde and dato["fin"] and dato["fin"] < desde:
            es_club, motivo = False, f"solo jugó la liga antes de {desde[:4]}"
        nombre = wd.etiqueta(e) or club
        paises = wd.valores(e, "P17")
        origen = "+".join(sorted(dato["origen"]))
        filas_csv.append({
            "liga": nombre_liga[liga],
            "club": nombre,
            "qid": club,
            "incluido": "sí" if es_club else "no",
            "motivo": motivo,
            "origen": origen,
            "temporadas": dato["temporadas"] or "",
            "desde": dato["inicio"] or "",
            "hasta": dato["fin"] or "",
            "wikipedias": wd.contar_wikipedias(e),
            "tipos_wikidata": ", ".join(tipos),
            "fichas_unidas": ", ".join(sorted(unidos.get(club, []))),
            "enlace": f"https://www.wikidata.org/wiki/{club}",
        })
        if es_club:
            c = aceptados.setdefault(club, {"nombre": nombre, "pais": paises[0] if paises else None, "ligas": {}})
            c["ligas"][liga] = {**dato, "origen": origen}

    # Nombres de los países de los clubes
    codigos_pais = {c["pais"] for c in aceptados.values() if c["pais"]}
    nombres_pais = {e["id"]: wd.etiqueta(e) or e["id"] for e in wd.entidades(codigos_pais, props="labels")}

    cambios = guardar(conn, ligas, aceptados, nombres_pais, ejecucion,
                      {e: v for e, v in alias.items() if v[0] in aceptados})

    salida = AQUI / "salida"
    salida.mkdir(exist_ok=True)
    with open(salida / "clubes_para_revisar.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(filas_csv[0].keys()))
        w.writeheader()
        w.writerows(filas_csv)

    por_liga = {}
    for l in ligas:
        filas = [f for f in filas_csv if f["liga"] == l["nombre"]]
        por_liga[l["nombre"]] = {
            "incluidos": sum(f["incluido"] == "sí" for f in filas),
            "descartados": sum(f["incluido"] == "no" for f in filas),
            "con_club": sum(f["incluido"] == "sí" and "club" in f["origen"] for f in filas),
            "con_temporadas": sum(f["incluido"] == "sí" and "temporadas" in f["origen"] for f in filas),
            "con_wikipedia": sum(f["incluido"] == "sí" and "wikipedia" in f["origen"] for f in filas),
            "sin_fechas": sum(f["incluido"] == "sí" and not f["desde"] and not f["hasta"] for f in filas),
        }
    return {
        "clubes": len(aceptados),
        "por_liga": por_liga,
        "cambios": cambios,
        "anterior": anterior[0].isoformat() if anterior else None,
    }


def guardar(conn, ligas, aceptados, nombres_pais, ejecucion, alias) -> dict:
    antes_clubes = {q: (n, p) for q, n, p in conn.execute("select qid, nombre, pais_qid from clubes")}
    antes_pares = {(c, l) for c, l in conn.execute("select club_qid, liga_qid from clubes_ligas")}
    ahora_pares = {(c, l) for c, d in aceptados.items() for l in d["ligas"]}
    cambios = {"clubes_nuevos": 0, "clubes_modificados": 0, "relaciones_nuevas": 0, "relaciones_eliminadas": 0}
    registro = []

    with conn.transaction():
        conn.cursor().executemany(
            """insert into ligas (qid, nombre, pais) values (%s, %s, %s)
               on conflict (qid) do update set nombre = excluded.nombre, pais = excluded.pais,
                 actualizado_en = now()""",
            [(l["qid"], l["nombre"], l["pais"]) for l in ligas],
        )
        conn.cursor().executemany(
            """insert into paises (qid, nombre) values (%s, %s)
               on conflict (qid) do update set nombre = excluded.nombre, actualizado_en = now()
               where paises.nombre is distinct from excluded.nombre""",
            list(nombres_pais.items()),
        )
        for q, c in aceptados.items():
            if q not in antes_clubes:
                cambios["clubes_nuevos"] += 1
                registro.append(("clubes", q, "nuevo", {"nombre": c["nombre"]}))
            elif antes_clubes[q] != (c["nombre"], c["pais"]):
                cambios["clubes_modificados"] += 1
                registro.append(("clubes", q, "modificado",
                                 {"antes": list(antes_clubes[q]), "ahora": [c["nombre"], c["pais"]]}))
        conn.cursor().executemany(
            """insert into clubes (qid, nombre, pais_qid, tipo, ultima_ejecucion) values (%s, %s, %s, 'club', %s)
               on conflict (qid) do update set nombre = excluded.nombre, pais_qid = excluded.pais_qid,
                 tipo = excluded.tipo, ultima_ejecucion = excluded.ultima_ejecucion,
                 actualizado_en = case when (clubes.nombre, clubes.pais_qid, clubes.tipo)
                   is distinct from (excluded.nombre, excluded.pais_qid, excluded.tipo)
                   then now() else clubes.actualizado_en end""",
            [(q, c["nombre"], c["pais"], ejecucion) for q, c in aceptados.items()],
        )
        conn.cursor().executemany(
            """insert into clubes_ligas (club_qid, liga_qid, inicio, fin, origen, temporadas)
               values (%s, %s, %s, %s, %s, %s)
               on conflict (club_qid, liga_qid) do update set inicio = excluded.inicio, fin = excluded.fin,
                 origen = excluded.origen, temporadas = excluded.temporadas,
                 actualizado_en = case when (clubes_ligas.inicio, clubes_ligas.fin, clubes_ligas.origen,
                   clubes_ligas.temporadas) is distinct from (excluded.inicio, excluded.fin,
                   excluded.origen, excluded.temporadas) then now() else clubes_ligas.actualizado_en end""",
            [(q, l, d["inicio"], d["fin"], d["origen"], d["temporadas"])
             for q, c in aceptados.items() for l, d in c["ligas"].items()],
        )
        conn.cursor().executemany(
            """insert into clubes_alias (qid, club_qid, motivo) values (%s, %s, %s)
               on conflict (qid) do update set club_qid = excluded.club_qid, motivo = excluded.motivo,
                 actualizado_en = case when (clubes_alias.club_qid, clubes_alias.motivo)
                   is distinct from (excluded.club_qid, excluded.motivo) then now()
                   else clubes_alias.actualizado_en end""",
            [(e, c, m) for e, (c, m) in alias.items()],
        )
        conn.execute("delete from clubes_alias where not (qid = any(%s))", (list(alias),))
        # Una ficha de equipo ya unida a su club no debe quedar también como club aparte.
        conn.execute("delete from clubes_ligas where club_qid = any(%s)", (list(alias),))
        conn.execute(
            "delete from clubes where qid = any(%s) and not exists "
            "(select 1 from pasos_por_club p where p.club_qid = clubes.qid)",
            (list(alias),),
        )
        for c, l in ahora_pares - antes_pares:
            cambios["relaciones_nuevas"] += 1
            registro.append(("clubes_ligas", f"{c}|{l}", "nuevo", None))
        # Si Wikidata ya no dice que un club estuvo en la liga, se quita la relación
        # (el club queda guardado por si algún jugador pasó por él).
        for c, l in antes_pares - ahora_pares:
            cambios["relaciones_eliminadas"] += 1
            registro.append(("clubes_ligas", f"{c}|{l}", "eliminado", None))
            conn.execute("delete from clubes_ligas where club_qid = %s and liga_qid = %s", (c, l))
        conn.cursor().executemany(
            "insert into cambios (ejecucion_id, tabla, registro, tipo, detalle) values (%s, %s, %s, %s, %s)",
            [(ejecucion, t, r, tipo, Jsonb(d) if d else None) for t, r, tipo, d in registro],
        )
    return cambios


def imprimir_reporte(r: dict) -> None:
    print("\n=== Reporte del paso 1: clubes ===")
    print(f"Clubes incluidos: {r['clubes']}")
    print("(una relación puede venir de varias fuentes a la vez)")
    print(f"{'Liga':<32}{'incl.':>6}{'desc.':>6}{'club':>6}{'temp.':>7}{'wikip.':>8}{'sin fechas':>11}")
    for liga, d in r["por_liga"].items():
        print(f"{liga:<32}{d['incluidos']:>6}{d['descartados']:>6}{d['con_club']:>6}"
              f"{d['con_temporadas']:>7}{d['con_wikipedia']:>8}{d['sin_fechas']:>11}")
    c = r["cambios"]
    desde = f"desde la ejecución del {r['anterior'][:16].replace('T', ' ')}" if r["anterior"] else "(primera ejecución)"
    print(f"\nCambios {desde}: {c['clubes_nuevos']} clubes nuevos, {c['clubes_modificados']} modificados, "
          f"{c['relaciones_nuevas']} relaciones club-liga nuevas, {c['relaciones_eliminadas']} eliminadas.")
    print("Lista completa para revisar: pipeline/salida/clubes_para_revisar.csv")


if __name__ == "__main__":
    main()
