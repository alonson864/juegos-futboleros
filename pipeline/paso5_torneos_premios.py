"""Paso 5: ediciones (con campeón) de los torneos relevantes y premios de todos los jugadores.

- Torneos (Champions, Mundial, Eurocopa, Copa América): cada edición con su campeón,
  desde Wikidata (P3450 "temporada de", P1346 "ganador").
- Premios (Balón de Oro, Bota de Oro, Puskás, etc.): para TODOS los jugadores de la base,
  desde Wikidata (P166 "premio recibido" con su año). Si Wikipedia (paso 4) ya registró
  ese premio y año para el jugador, no se duplica.

Los códigos de las competiciones se obtienen de los artículos de Wikipedia listados en
paso4_wikipedia.RELEVANTES. Se puede correr muchas veces sin duplicar nada.
Uso: pipeline/.venv/bin/python pipeline/paso5_torneos_premios.py
"""

from __future__ import annotations

import re
import sys
from datetime import date

import wikidata as wd
import wikipedia as wp
from db import conectar, iniciar_ejecucion, terminar_ejecucion
from paso4_wikipedia import RELEVANTES

PASO = "paso5_torneos_premios"

# Fichas que cuelgan del torneo pero no son una edición completa (fases, grupos, clasificatorias…)
NO_EDICION = re.compile(r"phase|stage|group|grupo|qualif|clasificaci|anexo|semifinal|ronda|round|"
                        r"participantes|knockout|play-off|final\b", re.I)


def anio(*valores: str | None) -> int | None:
    for v in valores:
        if v:
            m = re.match(r"^(\d{4})", v)
            if m:
                return int(m.group(1))
    return None


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)
    with conectar() as conn:
        ejecucion = iniciar_ejecucion(conn, PASO)
        try:
            resumen = correr(conn)
        except Exception as e:
            conn.rollback()
            terminar_ejecucion(conn, ejecucion, "error", {"error": str(e)[:500]})
            raise
        terminar_ejecucion(conn, ejecucion, "ok", resumen)

    print("\n=== Reporte del paso 5: torneos y premios ===")
    for nombre, d in resumen["torneos"].items():
        print(f"  {nombre:<40} {d['ediciones']:>4} ediciones, {d['con_campeon']:>4} con campeón")
        for x in d["sin_campeon"]:
            print(f"      sin campeón (revisar): {x}")
    print("Premios de jugadores de la base (desde Wikidata, sin duplicar Wikipedia):")
    for nombre, n in resumen["premios"].items():
        print(f"  {nombre:<40} {n:>4} nuevos")


def correr(conn) -> dict:
    qid_de = wp.qids_de_titulos(set(RELEVANTES))
    comps = {qid_de[t]: (t, tipo) for t, tipo in RELEVANTES.items() if t in qid_de}
    nombres = {e["id"]: wd.etiqueta(e) or comps[e["id"]][0] for e in
               wd.entidades(list(comps), props="labels", idiomas="es|en")}
    jugadores = {r[0] for r in conn.execute("select qid from jugadores")}
    conn.commit()

    cur = conn.cursor()
    cur.executemany(
        """insert into competiciones (qid, nombre, articulo_en, relevante, tipo) values (%s, %s, %s, true, %s)
           on conflict (qid) do update set nombre = excluded.nombre, articulo_en = excluded.articulo_en,
             relevante = true, tipo = excluded.tipo""",
        [(q, nombres.get(q, t), t, tipo) for q, (t, tipo) in comps.items()],
    )
    conn.commit()

    # --- Ediciones de torneos con su campeón ---
    torneos = {q: v for q, v in comps.items() if v[1] != "premio"}
    valores = " ".join("wd:" + q for q in torneos)
    print(f"Consultando ediciones de {len(torneos)} torneos…", flush=True)
    filas = wd.sparql(f"""
        SELECT ?comp ?ed ?edEs ?edEn ?t ?ini ?fin ?ganador ?ganEs ?ganEn WHERE {{
          VALUES ?comp {{ {valores} }}
          ?ed wdt:P3450 ?comp .
          OPTIONAL {{ ?ed rdfs:label ?edEs FILTER(LANG(?edEs) = "es") }}
          OPTIONAL {{ ?ed rdfs:label ?edEn FILTER(LANG(?edEn) = "en") }}
          OPTIONAL {{ ?ed wdt:P585 ?t }}
          OPTIONAL {{ ?ed wdt:P580 ?ini }}
          OPTIONAL {{ ?ed wdt:P582 ?fin }}
          OPTIONAL {{
            ?ed p:P1346 ?st . ?st ps:P1346 ?ganador .
            FILTER NOT EXISTS {{ ?st pq:P642 ?x }}       # sin calificador "de" (subcampeón, etc.)
            FILTER NOT EXISTS {{ ?st pq:P1352 ?rk FILTER(?rk != 1) }}
            OPTIONAL {{ ?ganador rdfs:label ?ganEs FILTER(LANG(?ganEs) = "es") }}
            OPTIONAL {{ ?ganador rdfs:label ?ganEn FILTER(LANG(?ganEn) = "en") }}
          }}
        }}""")
    ediciones: dict[str, tuple] = {}
    for f in filas:
        ed = wd.qid(f["ed"])
        actual = ediciones.get(ed)
        ganador = wd.qid(f["ganador"]) if "ganador" in f else None
        if actual and actual[5] and not ganador:
            continue
        ediciones[ed] = (
            ed, wd.qid(f["comp"]), f.get("edEs") or f.get("edEn") or ed,
            anio(f.get("fin"), f.get("t"), f.get("ini")),
            ganador, f.get("ganEs") or f.get("ganEn") if ganador else None,
        )
    # Se guardan las ediciones con campeón y, para revisar, las ya jugadas sin campeón que
    # parecen ediciones completas. Se descartan fases, grupos, clasificatorias y futuras.
    este_anio = date.today().year
    descartadas = [e for e in ediciones.values()
                   if not e[4] and (NO_EDICION.search(e[2]) or e[2] == e[0] or not e[3] or e[3] > este_anio)]
    for e in descartadas:
        del ediciones[e[0]]
    conn.execute("delete from ediciones where competicion_qid = any(%s) and not (qid = any(%s))",
                 (list(torneos), list(ediciones)))
    cur.executemany(
        """insert into ediciones (qid, competicion_qid, nombre, anio, campeon_qid, campeon_nombre)
           values (%s, %s, %s, %s, %s, %s)
           on conflict (qid) do update set competicion_qid = excluded.competicion_qid, nombre = excluded.nombre,
             anio = excluded.anio, campeon_qid = excluded.campeon_qid, campeon_nombre = excluded.campeon_nombre,
             actualizado_en = case when (ediciones.nombre, ediciones.anio, ediciones.campeon_qid)
               is distinct from (excluded.nombre, excluded.anio, excluded.campeon_qid)
               then now() else ediciones.actualizado_en end""",
        list(ediciones.values()),
    )
    conn.commit()
    resumen_torneos = {}
    for q, (t, _) in torneos.items():
        eds = [e for e in ediciones.values() if e[1] == q]
        resumen_torneos[nombres.get(q, t)] = {"ediciones": len(eds), "con_campeon": sum(1 for e in eds if e[4]),
                                              "sin_campeon": [f"{e[3]} {e[2]}" for e in eds if not e[4]]}

    # --- Premios: NO se toman de Wikidata ---
    # Wikidata confunde premios parecidos (p. ej. la Bota de Oro europea con la Bota de Oro
    # del Mundial), así que los premios salen solo del palmarés de Wikipedia (paso 4).
    conn.execute("delete from titulos_jugador where fuente = 'wikidata'")
    conn.commit()
    return {"torneos": resumen_torneos, "premios": {}}
    premios = {q: v for q, v in comps.items() if v[1] == "premio"}
    valores = " ".join("wd:" + q for q in premios)
    print(f"Consultando {len(premios)} premios en Wikidata…", flush=True)
    filas = wd.sparql(f"""
        SELECT ?j ?premio ?t WHERE {{
          VALUES ?premio {{ {valores} }}
          ?j p:P166 ?st . ?st ps:P166 ?premio .
          OPTIONAL {{ ?st pq:P585 ?t }}
        }}""")
    ya = {(j, c, a) for j, c, a in conn.execute(
        "select jugador_qid, competicion_qid, anio from titulos_jugador where competicion_qid = any(%s)",
        (list(premios),))}
    nuevos, conteo = [], {}
    for f in filas:
        j, c, a = wd.qid(f["j"]), wd.qid(f["premio"]), anio(f.get("t"))
        if j not in jugadores or not a or (j, c, a) in ya:
            continue
        ya.add((j, c, a))
        nuevos.append((f"{j}|{c}|{a}", j, c, nombres.get(c, premios[c][0]), str(a), a))
        conteo[nombres.get(c, c)] = conteo.get(nombres.get(c, c), 0) + 1
    cur.executemany(
        """insert into titulos_jugador (id, jugador_qid, competicion_qid, competicion_texto, temporada, anio,
             grupo, individual, fuente) values (%s, %s, %s, %s, %s, %s, 'Individual', true, 'wikidata')
           on conflict (id) do nothing""",
        nuevos,
    )
    conn.commit()
    return {"torneos": resumen_torneos, "premios": conteo}


if __name__ == "__main__":
    main()
