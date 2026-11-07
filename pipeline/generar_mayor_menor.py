"""Genera los jugadores del juego "Mayor o menor" (lee SOLO de la base).

Cinco categorías, cada jugador con su número:
  goles        goles en liga con clubes + goles con la selección mayor (ficha de Wikipedia)
  partidos     partidos en liga con clubes + partidos con la selección mayor (ficha de Wikipedia)
  titulos      títulos con sus clubes y su selección mayor (palmarés de Wikipedia;
               sin premios individuales, récords ni juveniles)
  fichajes     los fichajes más caros de la historia, en millones de euros (paso 9)
  asistencias  máximos asistidores de la Premier League (paso 9)

Solo entran jugadores reconocidos y con la ficha completa. La página arma con estos
jugadores cadenas con números parecidos (sin saltos obvios).
Uso: pipeline/.venv/bin/python pipeline/generar_mayor_menor.py
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict

from psycopg.types.json import Jsonb

import reconocidos
from db import conectar, iniciar_ejecucion, terminar_ejecucion
from nombres import normalizar

PASO = "generar_mayor_menor"
FAMOSOS = 700            # puesto máximo de fama para goles, partidos y títulos
MIN_WIKIPEDIAS = 50      # y fama mundial: artículo en al menos tantas Wikipedias
POR_CATEGORIA = 250       # como máximo, los más famosos de cada categoría
MINIMO = {"goles": 80, "partidos": 300, "titulos": 10}

JUVENIL = re.compile(r"\bU-?\d{2}\b|under-?\d{2}|olympic|youth|primavera|reserves|juvenil|\bB$|\bII$", re.I)
NO_TITULO = re.compile(
    r"award|player|team of|footballer|oscar|record|list of|golden|best|of the (year|season|month)|ballon|boot|"
    r"shoe|scorer|statistics|hall of fame|order of|medal|ranking|iffhs|fifpro|espn|goal \(|guardian|marca|"
    r"magazine|journalism|honour|prize|trophy of|athlete|personalit|sportsman|legend|selection", re.I)


def log(msg: str) -> None:
    print(msg, flush=True)


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
    log("\n=== Reporte: Mayor o menor ===")
    for cat, r in resumen.items():
        log(f"  {cat:<12} {r['jugadores']:>4} jugadores  (de {r['min']:g} a {r['max']:g})")


def _equipo(texto: str) -> str:
    return normalizar(re.sub(r"^→\s*|\(loan\)", "", texto or "")).strip()


def correr(conn) -> dict:
    rec = reconocidos.cargar(conn)
    fotos = reconocidos.fotos(conn)
    nombre = dict(conn.execute("select qid, nombre from jugadores_final where nombre !~ '^Q[0-9]+$'").fetchall())
    mundiales = {q for (q,) in conn.execute("select qid from jugadores_final where popularidad >= %s", (MIN_WIKIPEDIAS,))}
    conn.commit()
    famoso = {q for q in rec.jugadores & mundiales if rec.rango.get(q, 10**9) <= FAMOSOS}

    def item(cat, clave, q, valor, detalle, fuente):
        return {"id": f"{cat}|{clave}", "categoria": cat, "jugador_qid": q, "nombre": nombre.get(q, q),
                "valor": valor, "detalle": detalle, "foto": fotos.get(q), "fuente": fuente}

    # --- Goles y partidos: ficha de Wikipedia (liga con clubes + selección mayor) ---
    carrera: dict[str, list] = defaultdict(list)
    for q, sel, texto, pj, gl in conn.execute(
            "select jugador_qid, seleccion, equipo_texto, partidos, goles from carrera_wikipedia order by jugador_qid, orden"):
        carrera[q].append((sel, texto, pj, gl))
    equipos_de: dict[str, set[str]] = defaultdict(set)
    goles, partidos = {}, {}
    for q, filas in carrera.items():
        for sel, texto, _, _ in filas:
            if not JUVENIL.search(texto or ""):
                equipos_de[q].add(_equipo(texto))
        if q not in famoso:
            continue
        validas = [f for f in filas if not (f[0] and JUVENIL.search(f[1] or ""))]
        # Ficha incompleta (algún equipo sin número): no se usa
        if not validas or any(f[2] is None or f[3] is None for f in validas):
            continue
        goles[q] = sum(f[3] for f in validas)
        partidos[q] = sum(f[2] for f in validas)

    # --- Títulos: palmarés de Wikipedia, solo los ganados con sus clubes o su selección mayor ---
    premios = {q for (q,) in conn.execute("select qid from competiciones where tipo = 'premio'")}
    titulos: dict[str, set] = defaultdict(set)
    for q, comp_q, comp, grupo, anio, temporada in conn.execute(
            "select jugador_qid, competicion_qid, competicion_texto, grupo, anio, temporada from titulos_jugador "
            "where not individual"):
        if q not in famoso or comp_q in premios or NO_TITULO.search(comp) or not grupo or JUVENIL.search(grupo):
            continue
        g = _equipo(grupo)
        if not any(g == e or (len(g) >= 4 and (g in e or e in g)) for e in equipos_de.get(q, ())):
            continue
        if not (anio or re.search(r"\d", temporada or "")):
            continue
        titulos[q].add((comp_q or normalizar(comp), anio or temporada))
    conn.commit()

    def mas_famosos(valores: dict, cat: str, detalle: str) -> list[dict]:
        js = [q for q, v in valores.items() if v >= MINIMO[cat]]
        js.sort(key=lambda q: rec.rango.get(q, 10**9))
        return [item(cat, q, q, valores[q], detalle, "wikipedia_en") for q in js[:POR_CATEGORIA]]

    items = []
    items += mas_famosos(goles, "goles", "En liga con sus clubes y con su selección")
    items += mas_famosos(partidos, "partidos", "En liga con sus clubes y con su selección")
    items += mas_famosos({q: len(t) for q, t in titulos.items()}, "titulos", "Con sus clubes y su selección")

    # --- Fichajes y asistencias (paso 9) ---
    for fid, q, texto, origen, destino, monto, anio in conn.execute(
            "select id, jugador_qid, jugador_texto, origen, destino, monto_eur, anio from fichajes"):
        it = item("fichajes", fid, q or texto, float(monto), f"{origen} → {destino} ({anio})", "wikipedia_en")
        it["nombre"] = nombre.get(q, texto)
        items.append(it)
    for aid, q, texto, a, comp in conn.execute(
            "select id, jugador_qid, jugador_texto, asistencias, competicion from asistencias"):
        it = item("asistencias", aid, q or texto, a, f"En la {comp}", "wikipedia_en")
        it["nombre"] = nombre.get(q, texto)
        items.append(it)
    conn.commit()

    with conn.transaction():
        conn.execute("delete from mayor_menor_jugadores")
        conn.cursor().executemany(
            """insert into mayor_menor_jugadores (id, categoria, jugador_qid, nombre, valor, detalle, foto, fuente)
               values (%s, %s, %s, %s, %s, %s, %s, %s)""",
            [(i["id"], i["categoria"], i["jugador_qid"], i["nombre"], i["valor"], i["detalle"],
              Jsonb(i["foto"]) if i["foto"] else None, i["fuente"]) for i in items])

    resumen = {}
    for cat in ("goles", "asistencias", "titulos", "fichajes", "partidos"):
        vs = [i["valor"] for i in items if i["categoria"] == cat]
        resumen[cat] = {"jugadores": len(vs), "min": min(vs) if vs else 0, "max": max(vs) if vs else 0}
    return resumen


if __name__ == "__main__":
    main()
