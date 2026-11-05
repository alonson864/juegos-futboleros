"""Genera las categorías del juego "Último en pie" (lee SOLO de la base).

Categorías reconocibles pero específicas:
  clubes:        "Jugaron en Barcelona y en Real Madrid" (rivales directos: grandes del mismo país)
  nacion_club:   "Argentinos que jugaron en Real Madrid" / "Sudamericanos que jugaron en Chelsea"
  muchos_clubes: "Jugaron en más de 5 clubes"
  torneo_con:    "Jugaron un Mundial con Perú"
  titulo:     "Ganaron el Mundial / el Balón de Oro / la Bota de Oro…" (palmarés leído de Wikipedia)

Cada categoría guarda los códigos necesarios para que el buscador verifique a cualquier
jugador, cuántos jugadores conocidos la cumplen y algunos ejemplos para mostrar al final
de la ronda. Solo se crean categorías con suficientes jugadores conocidos para que la
ronda dure. Se puede correr muchas veces: reemplaza las categorías por las actuales.

Uso: pipeline/.venv/bin/python pipeline/generar_ultimo_en_pie.py
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from itertools import combinations

from psycopg.types.json import Jsonb

import dato_falso_titulos as titulos
from db import conectar, iniciar_ejecucion, terminar_ejecucion
from nombres import club_corto, nombre_seleccion

PASO = "generar_ultimo_en_pie"
CONOCIDO = 30          # Wikipedias: "jugador conocido" para contar miembros
MIN_CLUB = 15          # mínimo de jugadores conocidos para una categoría de un club
GRANDES_POR_PAIS = 6   # máximo de clubes "muy grandes" por país
PROPORCION_GRANDE = 0.6  # un club es "muy grande" si tiene al menos el 60 % de conocidos del más grande del país
MIN_PAR = 5            # mínimo para "jugaron en A y en B" (rivales del mismo país)
MIN_MUNDIAL = 10       # mínimo de mundialistas de esa selección
MIN_NACION_CLUB = 6    # "Argentinos que jugaron en Real Madrid": mínimo de jugadores conocidos
MIN_CONTINENTE_CLUB = 8
MAS_DE_CLUBES = 5      # "Jugaron en más de 5 clubes"

# Cómo se nombra a la gente de cada continente (según el nombre del continente en Wikidata)
CONTINENTE_PLURAL = {
    "América del Sur": "Sudamericanos",
    "África": "Africanos",
    "Asia": "Asiáticos",
    "América del Norte": "Norteamericanos",
    # "Europeos" no: en clubes europeos es casi todo el plantel.
}
MIN_TITULO = 8
DESTACADOS = 15


def gentilicio_plural(g: str | None) -> str | None:
    """'argentino' -> 'Argentinos', 'francés' -> 'Franceses', 'alemán' -> 'Alemanes'."""
    if not g or " " in g.strip():
        return None
    g = g.strip().lower()
    if g.endswith("és"):
        plural = g[:-2] + "eses"
    elif g.endswith("s"):
        plural = g
    elif g.endswith("án"):
        plural = g[:-2] + "anes"
    elif g[-1] in "aeiouáéíóú":
        plural = g + "s"
    else:
        plural = g + "es"
    return plural[:1].upper() + plural[1:]


# Filiales y reservas (Barcelona C, Castilla, Bayern II…): no cuentan como otro club
FILIAL = re.compile(r'(\s"?[BC]"?|\sII|\sReserves?|\sAcademy|\sCastilla|\sAtl[eè]tic|\sUnder-\d+|\sU\d+)$', re.I)


def dificultad(cantidad: int) -> str:
    return "facil" if cantidad >= 40 else "intermedio" if cantidad >= 15 else "dificil"


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
    print("\n=== Reporte: Último en pie ===")
    for tipo, n in resumen["por_tipo"].items():
        print(f"  {tipo:<10} {n} categorías")
    print(f"Total: {resumen['total']}  (fácil {resumen['por_dificultad'].get('facil', 0)}, "
          f"intermedio {resumen['por_dificultad'].get('intermedio', 0)}, "
          f"difícil {resumen['por_dificultad'].get('dificil', 0)})")


def correr(conn) -> dict:
    jugadores, nacionalidad = {}, {}
    for q, n, p, nacs in conn.execute(
            "select qid, nombre, popularidad, nacionalidades from jugadores_final where nombre !~ '^Q[0-9]+$'"):
        jugadores[q], nacionalidad[q] = (n, p), set(nacs or [])
    clubes = {q: (n, t, pais) for q, n, t, pais in conn.execute(
        "select qid, nombre, tipo, pais_qid from clubes_final")}
    paises, continente, gentilicio = {}, {}, {}
    for q, n, cont, gent in conn.execute("select qid, nombre, continente, gentilicio from paises"):
        paises[q], continente[q], gentilicio[q] = n, cont, gent
    de_liga = {r[0] for r in conn.execute("select distinct club_qid from clubes_ligas")}
    alias = defaultdict(set)
    for a, c in conn.execute("select qid, club_qid from clubes_alias"):
        alias[a].add(c)
        alias[c].add(a)

    # Equipo -> jugadores (pasos de Wikidata + carrera de Wikipedia, con fichas equivalentes)
    miembros: dict[str, set[str]] = defaultdict(set)
    clubes_de: dict[str, set[str]] = defaultdict(set)   # jugador -> clubes (fichas equivalentes unidas)
    for j, c in conn.execute(
            "select jugador_qid, club_qid from pasos_por_club_final "
            "union select jugador_qid, equipo_qid from carrera_wikipedia where equipo_qid is not null"):
        if j in jugadores:
            for x in {c} | alias[c]:
                miembros[x].add(j)
            if c in clubes and clubes[c][1] == "club" and not FILIAL.search(clubes[c][0]):
                clubes_de[j].add(min({c} | alias[c]))
    conn.commit()
    dt = titulos.cargar(conn)

    conocidos = lambda js: {j for j in js if jugadores[j][1] >= CONOCIDO}  # noqa: E731
    destacados = lambda js: [jugadores[j][0] for j in sorted(js, key=lambda j: -jugadores[j][1])[:DESTACADOS]]  # noqa: E731
    cats = []

    # --- Clubes MUY grandes: los GRANDES_POR_PAIS con más jugadores conocidos en cada país ---
    pais_de_club = dict(conn.execute(
        "select distinct on (cl.club_qid) cl.club_qid, l.pais from clubes_ligas cl join ligas l on l.qid = cl.liga_qid"
    ).fetchall())
    por_pais: dict[str, list] = defaultdict(list)
    for c in de_liga:
        if c in clubes and clubes[c][1] == "club" and c in pais_de_club:
            cs = conocidos(miembros[c])
            if len(cs) >= MIN_CLUB:
                por_pais[pais_de_club[c]].append((c, cs))
    grandes_por_pais = {}
    for p, cs in por_pais.items():
        cs = sorted(cs, key=lambda x: -len(x[1]))
        tope = len(cs[0][1]) * PROPORCION_GRANDE
        grandes_por_pais[p] = [x for x in cs if len(x[1]) >= tope][:GRANDES_POR_PAIS]

    for pais, grandes in grandes_por_pais.items():
        # Rivales directos: pares de grandes del MISMO país
        for (a, ma), (b, mb) in combinations(grandes, 2):
            comunes = ma & mb
            if len(comunes) >= MIN_PAR:
                na, nb = club_corto(clubes[a][0]), club_corto(clubes[b][0])
                cats.append({
                    "clave": f"clubes:{min(a, b)}|{max(a, b)}", "titulo": f"Jugaron en {na} y en {nb}",
                    "parametros": {"tipo": "clubes", "clubes": [sorted({a} | alias[a]), sorted({b} | alias[b])]},
                    "cantidad": len(comunes), "miembros": destacados(comunes),
                })

    # --- Nacionalidad o continente + club muy grande ("Argentinos que jugaron en Real Madrid") ---
    for pais_liga, grandes in grandes_por_pais.items():
        for c, cs in grandes:
            pais_club = clubes[c][2]
            nombre_club = club_corto(clubes[c][0])
            # Por nacionalidad (no la del propio club: "españoles en el Real Madrid" es demasiado amplio)
            por_nac: dict[str, set[str]] = defaultdict(set)
            for j in cs:
                for n in nacionalidad[j]:
                    por_nac[n].add(j)
            for n, js in por_nac.items():
                plural = gentilicio_plural(gentilicio.get(n))
                if n != pais_club and plural and len(js) >= MIN_NACION_CLUB:
                    cats.append({
                        "clave": f"nacion_club:{n}:{c}", "titulo": f"{plural} que jugaron en {nombre_club}",
                        "parametros": {"tipo": "nacion_club", "clubes": sorted({c} | alias[c]), "paises": [n]},
                        "cantidad": len(js), "miembros": destacados(js),
                    })
            # Por continente (de otro continente que el club)
            por_cont: dict[str, set[str]] = defaultdict(set)
            for j in cs:
                for n in nacionalidad[j]:
                    if continente.get(n):
                        por_cont[continente[n]].add(j)
            for cont, js in por_cont.items():
                if cont in CONTINENTE_PLURAL and cont != continente.get(pais_club) and len(js) >= MIN_CONTINENTE_CLUB:
                    del_cont = sorted(q for q, x in continente.items() if x == cont)
                    cats.append({
                        "clave": f"continente_club:{cont}:{c}",
                        "titulo": f"{CONTINENTE_PLURAL[cont]} que jugaron en {nombre_club}",
                        "parametros": {"tipo": "nacion_club", "clubes": sorted({c} | alias[c]), "paises": del_cont},
                        "cantidad": len(js), "miembros": destacados(js),
                    })

    # --- Jugaron en más de 5 clubes ---
    viajeros = conocidos({j for j, cs in clubes_de.items() if len(cs) > MAS_DE_CLUBES})
    cats.append({
        "clave": f"muchos_clubes:{MAS_DE_CLUBES}", "titulo": f"Jugaron en más de {MAS_DE_CLUBES} clubes",
        "parametros": {"tipo": "muchos_clubes", "minimo": MAS_DE_CLUBES + 1},
        "cantidad": len(viajeros), "miembros": destacados(viajeros),
    })

    # Selecciones mayores de cada jugador (para "Jugaron un Mundial con…")
    seleccion_de = defaultdict(set)
    nombre_sel = {c: nombre_seleccion(n, paises.get(p)) for c, (n, t, p) in clubes.items() if t == "seleccion"}
    for c in clubes:
        if nombre_sel.get(c):
            for j in miembros[c]:
                seleccion_de[j].add(c)

    # --- Jugaron un Mundial con [país] ---
    # Participó en un Mundial y jugó SOLO para esa selección mayor (si jugó para dos, no se
    # puede saber con cuál fue al Mundial, así que no cuenta).
    mundial = [q for q, f in dt.familia_de.items() if f == "mundial"]
    mundialistas = {r[0] for r in conn.execute(
        "select distinct jugador_qid from participaciones where competicion_qid = any(%s)", (mundial,))}
    conn.commit()
    for c, (nombre, tipo, pais) in clubes.items():
        if not nombre_sel.get(c):
            continue
        equipos = {c} | alias[c]
        js = {j for j in mundialistas if j in jugadores and seleccion_de.get(j) and seleccion_de[j] <= equipos}
        if len(js) >= MIN_MUNDIAL:
            cats.append({
                "clave": f"mundial_con:{c}", "titulo": f"Jugaron un Mundial con {nombre_sel[c]}",
                "parametros": {"tipo": "torneo_con", "competiciones": mundial, "equipos": sorted(equipos),
                               "pais": pais, "torneo": "un Mundial"},
                "cantidad": len(js), "miembros": destacados(js),
            })

    # --- Títulos (solo los de jugadores con palmarés leído) ---
    for fam in titulos.TEXTO:
        if fam not in dt.nombre_familia:
            continue
        ganadores = {j for j, ts in dt.titulos.items() if j in jugadores and any(f == fam for f, _ in ts)}
        if len(ganadores) >= MIN_TITULO:
            comps = sorted(q for q, f in dt.familia_de.items() if f == fam)
            cats.append({
                "clave": f"titulo:{fam}", "titulo": f"Ganaron {titulos.TEXTO[fam][0]}",
                "parametros": {"tipo": "titulo", "familia": fam, "competiciones": comps,
                               "individual": fam in titulos.PREMIOS},
                "cantidad": len(ganadores), "miembros": destacados(ganadores),
            })

    unicas: dict[str, dict] = {}
    for c in sorted(cats, key=lambda c: -c["cantidad"]):
        unicas.setdefault(c["titulo"], c)
    cats = list(unicas.values())

    with conn.transaction():
        conn.execute("delete from ultimo_en_pie_categorias")
        conn.cursor().executemany(
            """insert into ultimo_en_pie_categorias (clave, titulo, parametros, cantidad, miembros_destacados, dificultad)
               values (%s, %s, %s, %s, %s, %s)""",
            [(c["clave"], c["titulo"], Jsonb(c["parametros"]), c["cantidad"], Jsonb(c["miembros"]),
              dificultad(c["cantidad"])) for c in cats],
        )
    por_tipo: dict[str, int] = defaultdict(int)
    por_dif: dict[str, int] = defaultdict(int)
    for c in cats:
        por_tipo[c["parametros"]["tipo"]] += 1
        por_dif[dificultad(c["cantidad"])] += 1
    return {"total": len(cats), "por_tipo": dict(por_tipo), "por_dificultad": dict(por_dif)}


if __name__ == "__main__":
    main()
