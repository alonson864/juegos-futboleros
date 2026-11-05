"""Qué es "reconocible" para un hincha promedio. Lo usan los tres juegos.

- Jugadores reconocidos: los más visitados en Wikipedia (paso 7), no los de nicho.
- Selecciones grandes: las TOP_SELECCIONES con más fama sumada de sus jugadores,
  más las sudamericanas (Conmebol) que tienen jugadores reconocidos.
- Clubes grandes: en cada país de nuestras ligas, los que tienen más jugadores
  reconocidos (al menos PROPORCION del más grande del país, como máximo POR_PAIS).
Todo sale de la base; no hay listas escritas a mano.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from nombres import nombre_seleccion

JUGADORES_RECONOCIDOS = 3000      # los N más visitados
MIN_WIKIPEDIAS = 15               # además, artículo en al menos esta cantidad de Wikipedias
MAX_VISITAS_POR_WIKIPEDIA = 25_000  # más que esto suele ser tráfico automático o un pico pasajero
TOP_SELECCIONES = 15
MIN_RECONOCIDOS_CONMEBOL = 8      # selección sudamericana: al menos esta cantidad de reconocidos
CLUBES_POR_PAIS = 6
PROPORCION = 0.6
MIN_RECONOCIDOS_CLUB = 15


@dataclass
class Reconocidos:
    visitas: dict[str, int]                 # jugador -> visitas (0 si no hay dato)
    rango: dict[str, int]                   # jugador -> puesto por visitas (1 = el más visitado)
    jugadores: set[str]                     # los reconocidos
    selecciones: dict[str, str]             # selección grande -> nombre ("Argentina")
    clubes: dict[str, str]                  # club grande -> país de su liga
    alias: dict[str, set[str]]

    def tramo(self, desde: int, hasta: int) -> set[str]:
        """Jugadores entre los puestos `desde` y `hasta` por visitas."""
        return {j for j, r in self.rango.items() if desde <= r <= hasta}


def cargar(conn) -> Reconocidos:
    # Fama = visitas, recortadas si son desproporcionadas para su presencia en Wikipedia
    visitas, wikipedias = {}, {}
    for q, v, p in conn.execute(
            "select qid, visitas, popularidad from jugadores_final where nombre !~ '^Q[0-9]+$'"):
        visitas[q] = min(v or 0, (p or 0) * MAX_VISITAS_POR_WIKIPEDIA)
        wikipedias[q] = p or 0
    orden = sorted(visitas, key=lambda q: -visitas[q])
    rango = {q: i + 1 for i, q in enumerate(orden)}
    reconocidos = set([q for q in orden if wikipedias[q] >= MIN_WIKIPEDIAS][:JUGADORES_RECONOCIDOS])

    alias: dict[str, set[str]] = defaultdict(set)
    for a, c in conn.execute("select qid, club_qid from clubes_alias"):
        alias[a].add(c)
        alias[c].add(a)
    clubes = {q: (n, t, p) for q, n, t, p in conn.execute("select qid, nombre, tipo, pais_qid from clubes_final")}
    paises = {q: (n, cont) for q, n, cont in conn.execute("select qid, nombre, continente from paises")}

    miembros: dict[str, set[str]] = defaultdict(set)
    for j, c in conn.execute(
            "select jugador_qid, club_qid from pasos_por_club_final "
            "union select jugador_qid, equipo_qid from carrera_wikipedia where equipo_qid is not null"):
        if j in visitas:
            for x in {c} | alias[c]:
                miembros[x].add(j)

    # --- Selecciones grandes ---
    fama_sel: dict[str, int] = {}
    global_sel: dict[str, int] = {}
    nombre_sel: dict[str, str] = {}
    for c, (n, t, p) in clubes.items():
        if t != "seleccion":
            continue
        nombre = nombre_seleccion(n, paises.get(p, (None,))[0])
        if not nombre:
            continue
        nombre_sel[c] = nombre
        # Fama de la selección, con dos medidas que se corrigen entre sí:
        #  - visitas de sus 25 jugadores más visitados (favorece a la Premier, por la Wikipedia en inglés)
        #  - Wikipedias de sus 25 jugadores con más artículos (fama global)
        fama_sel[c] = sum(sorted((visitas[j] for j in miembros[c]), reverse=True)[:25])
        global_sel[c] = sum(sorted((wikipedias[j] for j in miembros[c]), reverse=True)[:25])
    rv = {c: i for i, c in enumerate(sorted(fama_sel, key=lambda c: -fama_sel[c]))}
    rw = {c: i for i, c in enumerate(sorted(global_sel, key=lambda c: -global_sel[c]))}
    top = sorted(fama_sel, key=lambda c: rv[c] + rw[c])[:TOP_SELECCIONES]
    conmebol = [c for c in fama_sel if paises.get(clubes[c][2], (None, None))[1] == "América del Sur"
                and len(miembros[c] & reconocidos) >= MIN_RECONOCIDOS_CONMEBOL]
    selecciones = {c: nombre_sel[c] for c in set(top) | set(conmebol)}

    # --- Clubes grandes por país (de nuestras ligas) ---
    pais_liga = dict(conn.execute(
        "select distinct on (cl.club_qid) cl.club_qid, l.pais from clubes_ligas cl join ligas l on l.qid = cl.liga_qid"
    ).fetchall())
    por_pais: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for c, pais in pais_liga.items():
        if c in clubes and clubes[c][1] == "club":
            n = len(miembros[c] & reconocidos)
            if n >= MIN_RECONOCIDOS_CLUB:
                por_pais[pais].append((c, n))
    grandes: dict[str, str] = {}
    for pais, lista in por_pais.items():
        lista.sort(key=lambda x: -x[1])
        tope = lista[0][1] * PROPORCION
        for c, n in lista[:CLUBES_POR_PAIS]:
            if n >= tope:
                grandes[c] = pais
    conn.commit()
    return Reconocidos(visitas, rango, reconocidos, selecciones, grandes, alias)


def fotos(conn) -> dict[str, dict]:
    """jugador -> foto usable (miniatura de Commons con autor y licencia libre)."""
    salida = {}
    for q, url, autor, lic, lic_url in conn.execute(
            "select jugador_qid, url_miniatura, autor, licencia, licencia_url from imagenes_final "
            "where licencia_libre and url_miniatura is not null"):
        salida[q] = {"url": url, "autor": autor or "Autor desconocido", "licencia": lic, "licencia_url": lic_url}
    conn.commit()
    return salida
