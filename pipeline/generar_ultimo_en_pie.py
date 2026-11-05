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
import reconocidos
from db import conectar, iniciar_ejecucion, terminar_ejecucion
from nombres import club_corto, nombre_seleccion

PASO = "generar_ultimo_en_pie"
CONOCIDO = 30          # Wikipedias: "jugador conocido" para contar miembros
MIN_CLUB = 15          # mínimo de jugadores conocidos para una categoría de un club
GRANDES_POR_PAIS = 6   # máximo de clubes "muy grandes" por país
PROPORCION_GRANDE = 0.6  # un club es "muy grande" si tiene al menos el 60 % de conocidos del más grande del país
MIN_PAR = 5            # mínimo para "jugaron en A y en B" (rivales del mismo país)
MIN_MUNDIAL = 8        # mínimo de mundialistas de esa selección
MIN_NACION_CLUB = 5    # "Argentinos que jugaron en Real Madrid": mínimo de jugadores reconocidos
MIN_CONTINENTE_CLUB = 6
MAS_DE_CLUBES = 5      # "Jugaron en más de 5 clubes"
MIN_PORTEROS = 4
MIN_CAMPEONES = 5
MIN_DOBLE = 6
# Combinaciones de dos títulos
DOBLES = [("champions", "mundial"), ("balon_de_oro", "mundial"), ("champions", "eurocopa"),
          ("balon_de_oro", "champions"), ("mundial", "copa_america")]

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
    rec = reconocidos.cargar(conn)
    foto = reconocidos.fotos(conn)
    jugadores, nacionalidad, posiciones = {}, {}, {}
    for q, n, nacs, pos in conn.execute(
            "select qid, nombre, nacionalidades, posiciones from jugadores_final where nombre !~ '^Q[0-9]+$'"):
        jugadores[q], nacionalidad[q], posiciones[q] = n, set(nacs or []), set(pos or [])
    clubes = {q: (n, t, pais) for q, n, t, pais in conn.execute("select qid, nombre, tipo, pais_qid from clubes_final")}
    paises, continente, gentilicio = {}, {}, {}
    for q, n, cont, gent in conn.execute("select qid, nombre, continente, gentilicio from paises"):
        paises[q], continente[q], gentilicio[q] = n, cont, gent
    portero = [q for q, n in conn.execute("select qid, nombre from posiciones") if re.search(r"guardameta|portero|arquero", n, re.I)]
    alias = rec.alias

    miembros: dict[str, set[str]] = defaultdict(set)
    clubes_de: dict[str, set[str]] = defaultdict(set)
    for j, c in conn.execute(
            "select jugador_qid, club_qid from pasos_por_club_final "
            "union select jugador_qid, equipo_qid from carrera_wikipedia where equipo_qid is not null"):
        if j in jugadores:
            for x in {c} | alias[c]:
                miembros[x].add(j)
            if c in clubes and clubes[c][1] == "club" and not FILIAL.search(clubes[c][0]):
                clubes_de[j].add(min({c} | alias[c]))
    seleccion_de: dict[str, set[str]] = defaultdict(set)      # jugador -> selecciones mayores
    for c, (n, t, p) in clubes.items():
        if t == "seleccion" and nombre_seleccion(n, paises.get(p)):
            for j in miembros[c]:
                seleccion_de[j].add(c)
    mundial = [r[0] for r in conn.execute(
        "select qid from competiciones where articulo_en = 'FIFA World Cup'")]
    mundialistas = {r[0] for r in conn.execute(
        "select distinct jugador_qid from participaciones where competicion_qid = any(%s)", (mundial,))}
    conn.commit()
    dt = titulos.cargar(conn)

    R = rec.jugadores                                            # jugadores reconocidos
    def destacados(js):
        orden = sorted(js, key=lambda j: -rec.visitas.get(j, 0))[:DESTACADOS]
        return [{"nombre": jugadores[j], **({"foto": foto[j]} if j in foto else {})} for j in orden]
    def agregar(clave, titulo, parametros, js):
        cats.append({"clave": clave, "titulo": titulo, "parametros": parametros,
                     "cantidad": len(js), "miembros": destacados(js)})
    eq = lambda c: sorted({c} | alias[c])                        # noqa: E731
    nombre_club = lambda c: club_corto(clubes[c][0])             # noqa: E731
    cats: list[dict] = []

    grandes = {c: p for c, p in rec.clubes.items() if c in clubes}
    por_pais: dict[str, list[str]] = defaultdict(list)
    for c, p in grandes.items():
        por_pais[p].append(c)

    # 1) Rivales directos (grandes del mismo país)
    for p, cs in por_pais.items():
        for a, b in combinations(sorted(cs), 2):
            js = miembros[a] & miembros[b] & R
            if len(js) >= MIN_PAR:
                agregar(f"clubes:{a}|{b}", f"Jugaron en {nombre_club(a)} y en {nombre_club(b)}",
                        {"tipo": "clubes", "clubes": [eq(a), eq(b)]}, js)

    # 2) Grandes de distintos países (los 12 con más reconocidos)
    top = sorted(grandes, key=lambda c: -len(miembros[c] & R))[:12]
    for a, b in combinations(top, 2):
        if grandes[a] != grandes[b]:
            js = miembros[a] & miembros[b] & R
            if len(js) >= MIN_PAR:
                agregar(f"clubes:{min(a, b)}|{max(a, b)}", f"Jugaron en {nombre_club(a)} y en {nombre_club(b)}",
                        {"tipo": "clubes", "clubes": [eq(a), eq(b)]}, js)

    # 3) Nacionalidad (solo de selecciones grandes) o continente + club grande
    paises_grandes = {clubes[c][2] for c in rec.selecciones if clubes[c][2]}
    for c in grandes:
        pais_club = clubes[c][2]
        for n in paises_grandes - {pais_club}:
            js = {j for j in miembros[c] & R if n in nacionalidad[j]}
            plural = gentilicio_plural(gentilicio.get(n))
            if plural and len(js) >= MIN_NACION_CLUB:
                agregar(f"nacion_club:{n}:{c}", f"{plural} que jugaron en {nombre_club(c)}",
                        {"tipo": "nacion_club", "clubes": eq(c), "paises": [n]}, js)
        for cont, plural in CONTINENTE_PLURAL.items():
            if cont == continente.get(pais_club):
                continue
            del_cont = {q for q, x in continente.items() if x == cont}
            js = {j for j in miembros[c] & R if nacionalidad[j] & del_cont}
            if len(js) >= MIN_CONTINENTE_CLUB:
                agregar(f"continente_club:{cont}:{c}", f"{plural} que jugaron en {nombre_club(c)}",
                        {"tipo": "nacion_club", "clubes": eq(c), "paises": sorted(del_cont)}, js)

    # 4) Porteros que jugaron en un club grande
    for c in grandes:
        js = {j for j in miembros[c] if posiciones[j] & set(portero) and rec.rango.get(j, 10**9) <= 6000}
        if len(js) >= MIN_PORTEROS:
            agregar(f"porteros:{c}", f"Porteros que jugaron en {nombre_club(c)}",
                    {"tipo": "posicion_club", "clubes": eq(c), "posiciones": portero}, js)

    # 5) Jugaron un Mundial con… (selecciones grandes y Conmebol)
    for c, nombre in rec.selecciones.items():
        equipos = set(eq(c))
        js = {j for j in mundialistas if j in jugadores and seleccion_de.get(j) and seleccion_de[j] <= equipos}
        if len(js) >= MIN_MUNDIAL:
            agregar(f"mundial_con:{c}", f"Jugaron un Mundial con {nombre}",
                    {"tipo": "torneo_con", "competiciones": mundial, "equipos": sorted(equipos),
                     "pais": clubes[c][2], "torneo": "un Mundial"}, js)

    # 6) Campeones del mundo con… (título del Mundial y solo esa selección mayor)
    comps = {f: sorted(q for q, x in dt.familia_de.items() if x == f) for f in titulos.TEXTO}
    for c, nombre in rec.selecciones.items():
        equipos = set(eq(c))
        js = {j for j, ts in dt.titulos.items() if j in jugadores and any(f == "mundial" for f, _ in ts)
              and seleccion_de.get(j) and seleccion_de[j] <= equipos}
        if len(js) >= MIN_CAMPEONES:
            agregar(f"campeones_con:{c}", f"Campeones del mundo con {nombre}",
                    {"tipo": "titulo_con", "competiciones": comps["mundial"], "equipos": sorted(equipos)}, js)

    # 7) Títulos (uno o dos)
    def ganaron(fam):
        return {j for j, ts in dt.titulos.items() if j in jugadores and any(f == fam for f, _ in ts)}
    for fam in titulos.TEXTO:
        js = ganaron(fam)
        if fam in dt.nombre_familia and len(js) >= MIN_TITULO:
            agregar(f"titulo:{fam}", f"Ganaron {titulos.TEXTO[fam][0]}",
                    {"tipo": "titulo", "familia": fam, "competiciones": comps[fam],
                     "individual": fam in titulos.PREMIOS}, js)
    for a, b in DOBLES:
        js = ganaron(a) & ganaron(b)
        if len(js) >= MIN_DOBLE:
            agregar(f"titulos:{a}+{b}", f"Ganaron {titulos.TEXTO[a][0]} y {titulos.TEXTO[b][0]}",
                    {"tipo": "titulos", "grupos": [
                        {"competiciones": comps[a], "individual": a in titulos.PREMIOS},
                        {"competiciones": comps[b], "individual": b in titulos.PREMIOS}]}, js)

    # 8) Jugaron en más de 5 clubes
    agregar(f"muchos_clubes:{MAS_DE_CLUBES}", f"Jugaron en más de {MAS_DE_CLUBES} clubes",
            {"tipo": "muchos_clubes", "minimo": MAS_DE_CLUBES + 1},
            {j for j, cs in clubes_de.items() if len(cs) > MAS_DE_CLUBES} & R)

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
