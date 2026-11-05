"""Genera preguntas del juego "Dato Falso Futbolero" leyendo SOLO de la base.

Tipos de pregunta:
  1. clubes_de_jugador:  "[Jugador] jugó en todos estos clubes"  (4 clubes reales + 1 falso)
  2. jugadores_de_club:  "Todos estos jugaron en [club]"          (4 jugadores que sí + 1 que no)
  3. jugadores_de_pais:  "Todos estos jugadores son de [país]"    (4 que sí + 1 que no)

Seguridad:
  - Solo se usan jugadores con fecha de inicio en todos sus pasos por clubes
    (la fecha de fin solo puede faltar en su club actual, el más reciente).
  - Antes de usar una opción como falsa se verifica que no aparezca en NINGÚN
    registro del jugador: pasos originales, pasos con correcciones, la tabla de
    correcciones y las fichas equivalentes del mismo club (clubes_alias).
  - En cada ejecución se vuelven a validar TODAS las preguntas guardadas con los
    datos actuales, y se borran las que ya no sean correctas.

Opción falsa creíble: se puntúa por club de un excompañero, misma liga, mismo país
y misma época. La dificultad decide cuán creíble debe ser y cuán conocidos son
los jugadores.

Uso: pipeline/.venv/bin/python pipeline/generar_dato_falso.py [--por-tipo 30]
"""

from __future__ import annotations

import argparse
import random
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from psycopg.types.json import Jsonb

import dato_falso_titulos as titulos
from nombres import club_corto
from db import conectar, iniciar_ejecucion, terminar_ejecucion

PASO = "generar_dato_falso"
HOY = date.today()

# Popularidad = número de Wikipedias con artículo
DIFICULTADES = {
    #             popularidad mínima, máxima, credibilidad mínima de la falsa (0 a 1)
    "facil":      (60, 10_000, 0.0),
    "intermedio": (30, 59, 0.35),
    "dificil":    (10, 29, 0.6),
}


@dataclass
class Paso:
    club: str
    inicio: date | None
    fin: date | None


@dataclass
class Jugador:
    qid: str
    nombre: str
    popularidad: int
    nacionalidades: set[str]
    pasos: list[Paso] = field(default_factory=list)        # solo clubes (tipo 'club')
    selecciones: set[str] = field(default_factory=set)      # países de selecciones en que jugó
    registros_club: set[str] = field(default_factory=set)   # TODO club que aparece en cualquier registro
    registros_pais: set[str] = field(default_factory=set)   # TODO país ligado (nacionalidad o selección)

    def fechas_completas(self) -> bool:
        if len(self.pasos) == 0 or any(p.inicio is None for p in self.pasos):
            return False
        sin_fin = [p for p in self.pasos if p.fin is None]
        if not sin_fin:
            return True
        ultimo = max(self.pasos, key=lambda p: p.inicio)
        return len(sin_fin) == 1 and sin_fin[0] is ultimo

    def clubes(self) -> list[str]:
        vistos, salida = set(), []
        for p in sorted(self.pasos, key=lambda p: p.inicio or date.min):
            if p.club not in vistos:
                vistos.add(p.club)
                salida.append(p.club)
        return salida


def se_cruzan(a: Paso, b: Paso) -> bool:
    return (a.inicio or date.min) <= (b.fin or HOY) and (b.inicio or date.min) <= (a.fin or HOY)


# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------

def cargar(conn):
    jug: dict[str, Jugador] = {}
    for q, n, pop, nacs in conn.execute(
            "select qid, nombre, popularidad, nacionalidades from jugadores_final where nombre !~ '^Q[0-9]+$'"):
        jug[q] = Jugador(q, n, pop, set(nacs or []))

    # Nombres cortos para mostrar ("Fulham" en vez de "Fulham Football Club")
    clubes = {q: (club_corto(n) if t == "club" else n, t, p)
              for q, n, t, p in conn.execute("select qid, nombre, tipo, pais_qid from clubes_final")}
    paises = dict(conn.execute("select qid, nombre from paises").fetchall())

    for j, c, ini, fin in conn.execute(
            "select jugador_qid, club_qid, inicio, fin from pasos_por_club_final"):
        if j not in jug or c not in clubes:
            continue
        tipo, pais = clubes[c][1], clubes[c][2]
        if tipo == "club":
            jug[j].pasos.append(Paso(c, ini, fin))
        elif tipo in ("seleccion", "seleccion_juvenil") and pais:
            jug[j].selecciones.add(pais)

    # --- Todos los registros, para la verificación de seguridad ---
    alias_de = defaultdict(set)  # club -> fichas equivalentes (en ambos sentidos)
    for a, c in conn.execute("select qid, club_qid from clubes_alias"):
        alias_de[a].add(c)
        alias_de[c].add(a)

    def con_alias(cs: set[str]) -> set[str]:
        return cs | {x for c in cs for x in alias_de[c]}

    # pasos originales (sin correcciones) y con correcciones
    for j, c in conn.execute("select jugador_qid, club_qid from pasos_por_club "
                             "union select jugador_qid, club_qid from pasos_por_club_final"):
        if j in jug:
            jug[j].registros_club.add(c)
    # correcciones que cambian el club de un paso
    for j, valor in conn.execute(
            """select p.jugador_qid, c.valor from correcciones c
               join pasos_por_club p on p.id_wikidata = c.registro
               where c.tabla = 'pasos_por_club' and c.campo = 'club_qid'"""):
        if j in jug and isinstance(valor, str):
            jug[j].registros_club.add(valor)
    # correcciones de nacionalidad
    nac_corr = defaultdict(set)
    for j, valor in conn.execute(
            "select registro, valor from correcciones where tabla = 'jugadores' and campo = 'nacionalidades'"):
        if isinstance(valor, list):
            nac_corr[j].update(v for v in valor if isinstance(v, str))
    # nacionalidades originales (sin corrección)
    nac_orig = {q: set(n or []) for q, n in conn.execute("select qid, nacionalidades from jugadores")}

    for j in jug.values():
        j.registros_club = con_alias(j.registros_club)
        j.registros_pais = j.nacionalidades | nac_orig.get(j.qid, set()) | nac_corr[j.qid] | j.selecciones
        # selecciones vistas en registros originales (también las excluidas por corrección)
        j.registros_pais |= {clubes[c][2] for c in j.registros_club
                             if c in clubes and clubes[c][1] in ("seleccion", "seleccion_juvenil") and clubes[c][2]}

    liga_de = defaultdict(set)
    for c, l in conn.execute("select club_qid, liga_qid from clubes_ligas"):
        liga_de[c].add(l)
    conn.commit()
    return jug, clubes, paises, liga_de


# ---------------------------------------------------------------------------
# Credibilidad de una opción falsa (0 a 1)
# ---------------------------------------------------------------------------

def companeros(j: Jugador, por_club: dict[str, list[tuple[str, Paso]]]) -> set[str]:
    salida = set()
    for p in j.pasos:
        for otro, q in por_club.get(p.club, []):
            if otro != j.qid and se_cruzan(p, q):
                salida.add(otro)
    return salida


def credibilidad_club(j: Jugador, club: str, ctx) -> float:
    jug, clubes, liga_de, por_club, comp = ctx
    puntos = 0.0
    if any(club in jug[o].registros_club for o in comp.get(j.qid, ())):
        puntos += 0.45                                    # club de un excompañero
    ligas_j = set().union(*(liga_de[c] for c in j.clubes())) if j.pasos else set()
    if liga_de[club] & ligas_j:
        puntos += 0.3                                     # misma liga
    paises_j = {clubes[c][2] for c in j.clubes() if c in clubes}
    if clubes.get(club, (None, None, None))[2] in paises_j:
        puntos += 0.1                                     # mismo país
    # misma época: el club tuvo jugadores conocidos mientras él jugaba
    if any(se_cruzan(p, q) for _, q in por_club.get(club, []) for p in j.pasos):
        puntos += 0.15
    return min(puntos, 1.0)


def credibilidad_jugador_en_club(falso: Jugador, club: str, verdaderos: list[Jugador], ctx) -> float:
    jug, clubes, liga_de, por_club, comp = ctx
    puntos = 0.0
    if any(v.qid in comp.get(falso.qid, ()) for v in verdaderos):
        puntos += 0.45                                    # compañero de alguno de los verdaderos
    if any(liga_de[c] & liga_de[club] for c in falso.clubes()):
        puntos += 0.3                                     # jugó en la misma liga
    if any(clubes.get(c, (0, 0, 0))[2] == clubes[club][2] for c in falso.clubes()):
        puntos += 0.1                                     # jugó en el mismo país
    pasos_club = [q for _, q in por_club.get(club, [])]
    if any(se_cruzan(p, q) for p in falso.pasos for q in pasos_club):
        puntos += 0.15                                    # misma época
    return min(puntos, 1.0)


def credibilidad_jugador_de_pais(falso: Jugador, pais: str, verdaderos: list[Jugador], ctx) -> float:
    jug, clubes, liga_de, por_club, comp = ctx
    puntos = 0.0
    if any(clubes.get(c, (0, 0, 0))[2] == pais for c in falso.clubes()):
        puntos += 0.45                                    # jugó en un club de ese país
    if any(v.qid in comp.get(falso.qid, ()) for v in verdaderos):
        puntos += 0.35                                    # compañero de alguno de los verdaderos
    if any(set(falso.clubes()) & set(v.clubes()) for v in verdaderos):
        puntos += 0.2                                     # comparte club (en otra época)
    return min(puntos, 1.0)


# ---------------------------------------------------------------------------
# Validación (se usa al crear y al revalidar)
# ---------------------------------------------------------------------------

def es_valida(p: dict, jug: dict[str, Jugador]) -> bool:
    prot = p["protagonista"]
    ops = p["opciones"]
    falsas = [o for o in ops if not o["verdadera"]]
    verdaderas = [o for o in ops if o["verdadera"]]
    if len(ops) != 5 or len(falsas) != 1:
        return False
    f = falsas[0]["qid"]
    if p["tipo"] == "clubes_de_jugador":
        j = jug.get(prot["qid"])
        return bool(j and j.fechas_completas()
                    and f not in j.registros_club
                    and all(o["qid"] in j.clubes() for o in verdaderas))
    if p["tipo"] == "jugadores_de_club":
        club = prot["qid"]
        fj = jug.get(f)
        vs = [jug.get(o["qid"]) for o in verdaderas]
        return bool(fj and fj.fechas_completas() and club not in fj.registros_club
                    and all(v and v.fechas_completas() and club in v.clubes() for v in vs))
    if p["tipo"] == "jugadores_de_pais":
        pais = prot["qid"]
        fj = jug.get(f)
        vs = [jug.get(o["qid"]) for o in verdaderas]
        return bool(fj and fj.fechas_completas() and pais not in fj.registros_pais
                    and all(v and v.fechas_completas() and pais in v.nacionalidades for v in vs))
    return False


# ---------------------------------------------------------------------------
# Generadores
# ---------------------------------------------------------------------------

def mezclar(opciones: list[dict], rng: random.Random) -> list[dict]:
    rng.shuffle(opciones)
    return opciones


def lista(nombres: list[str]) -> str:
    return nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " y " + nombres[-1]


def gen_clubes_de_jugador(elegibles, dif, ctx, rng, n):
    jug, clubes, liga_de, por_club, comp = ctx
    pmin, pmax, cmin = DIFICULTADES[dif]
    candidatos = [j for j in elegibles if pmin <= j.popularidad <= pmax and len(j.clubes()) >= 4]
    rng.shuffle(candidatos)
    for j in candidatos:
        # Posibles falsos: clubes de ligas de la base donde nunca estuvo
        posibles = {c for c in por_club if clubes[c][1] == "club" and c not in j.registros_club}
        puntuados = sorted(((credibilidad_club(j, c, ctx), c) for c in posibles), reverse=True)
        puntuados = [(s, c) for s, c in puntuados if s >= cmin]
        if dif == "facil":
            puntuados = [(s, c) for s, c in puntuados if s <= 0.6]   # algo distinguible
        if not puntuados:
            continue
        _, falso = rng.choice(puntuados[:5])
        # Preferir clubes de nuestras ligas (más reconocibles) para las verdaderas
        reales = sorted(j.clubes(), key=lambda c: (not liga_de[c], rng.random()))[:4]
        opciones = [{"texto": clubes[c][0], "qid": c, "verdadera": True} for c in reales]
        opciones.append({"texto": clubes[falso][0], "qid": falso, "verdadera": False})
        yield {
            "clave": f"clubes_de_jugador:{j.qid}:{falso}",
            "tipo": "clubes_de_jugador",
            "dificultad": dif,
            "afirmacion": f"{j.nombre} jugó en todos estos clubes",
            "protagonista": {"tipo": "jugador", "qid": j.qid, "nombre": j.nombre},
            "opciones": mezclar(opciones, rng),
            "explicacion": f"{j.nombre} jugó en {lista([clubes[c][0] for c in j.clubes()])}. "
                           f"Nunca jugó en {clubes[falso][0]}.",
        }
        n -= 1
        if n == 0:
            return


def gen_jugadores_de_club(elegibles, dif, ctx, rng, n):
    jug, clubes, liga_de, por_club, comp = ctx
    pmin, pmax, cmin = DIFICULTADES[dif]
    clubs = [c for c in por_club if liga_de[c]]
    rng.shuffle(clubs)
    en_rango = [f for f in elegibles if pmin <= f.popularidad <= pmax]
    ligas_jug = {f.qid: set().union(*(liga_de[c] for c in f.clubes())) for f in en_rango}
    for club in clubs:
        miembros = list({q: jug[q] for q, _ in por_club[club] if pmin <= jug[q].popularidad <= pmax}.values())
        if len(miembros) < 4:
            continue
        verdaderos = rng.sample(sorted(miembros, key=lambda m: -m.popularidad)[:12], 4)
        cercanos = set().union(*(comp.get(v.qid, set()) for v in verdaderos))
        posibles = [f for f in en_rango if club not in f.registros_club
                    and (ligas_jug[f.qid] & liga_de[club] or f.qid in cercanos)]
        puntuados = sorted(((credibilidad_jugador_en_club(f, club, verdaderos, ctx), f.qid) for f in posibles),
                           reverse=True)
        puntuados = [(s, q) for s, q in puntuados if s >= cmin and (dif != "facil" or s <= 0.6)]
        if not puntuados:
            continue
        _, fq = rng.choice(puntuados[:5])
        falso = jug[fq]
        nombre_club = clubes[club][0]
        opciones = [{"texto": v.nombre, "qid": v.qid, "verdadera": True} for v in verdaderos]
        opciones.append({"texto": falso.nombre, "qid": falso.qid, "verdadera": False})
        yield {
            "clave": f"jugadores_de_club:{club}:{falso.qid}",
            "tipo": "jugadores_de_club",
            "dificultad": dif,
            "afirmacion": f"Todos estos jugaron en {nombre_club}",
            "protagonista": {"tipo": "club", "qid": club, "nombre": nombre_club},
            "opciones": mezclar(opciones, rng),
            "explicacion": f"{lista([v.nombre for v in verdaderos])} jugaron en {nombre_club}. "
                           f"{falso.nombre} nunca jugó ahí: jugó en {lista([clubes[c][0] for c in falso.clubes()[:5]])}.",
        }
        n -= 1
        if n == 0:
            return


def gen_jugadores_de_pais(elegibles, dif, ctx, rng, n, paises):
    jug, clubes, liga_de, por_club, comp = ctx
    pmin, pmax, cmin = DIFICULTADES[dif]
    por_pais = defaultdict(list)
    for j in elegibles:
        if pmin <= j.popularidad <= pmax and len(j.nacionalidades) == 1:  # evita doble nacionalidad
            por_pais[next(iter(j.nacionalidades))].append(j)
    lista_paises = [p for p, js in por_pais.items() if len(js) >= 4 and p in paises]
    rng.shuffle(lista_paises)
    for pais in lista_paises:
        verdaderos = rng.sample(sorted(por_pais[pais], key=lambda m: -m.popularidad)[:12], 4)
        cercanos = set().union(*(comp.get(v.qid, set()) for v in verdaderos))
        posibles = [f for f in elegibles if pmin <= f.popularidad <= pmax and pais not in f.registros_pais
                    and f.nacionalidades
                    and (f.qid in cercanos or any(clubes.get(c, (0, 0, 0))[2] == pais for c in f.clubes()))]
        puntuados = sorted(((credibilidad_jugador_de_pais(f, pais, verdaderos, ctx), f.qid) for f in posibles),
                           reverse=True)
        puntuados = [(s, q) for s, q in puntuados if s >= cmin and (dif != "facil" or s <= 0.6)]
        if not puntuados:
            continue
        _, fq = rng.choice(puntuados[:5])
        falso = jug[fq]
        nombre_pais = paises[pais]
        de_falso = lista([paises.get(n, n) for n in sorted(falso.nacionalidades)])
        opciones = [{"texto": v.nombre, "qid": v.qid, "verdadera": True} for v in verdaderos]
        opciones.append({"texto": falso.nombre, "qid": falso.qid, "verdadera": False})
        yield {
            "clave": f"jugadores_de_pais:{pais}:{falso.qid}",
            "tipo": "jugadores_de_pais",
            "dificultad": dif,
            "afirmacion": f"Todos estos jugadores son de {nombre_pais}",
            "protagonista": {"tipo": "pais", "qid": pais, "nombre": nombre_pais},
            "opciones": mezclar(opciones, rng),
            "explicacion": f"{lista([v.nombre for v in verdaderos])} son de {nombre_pais}. "
                           f"{falso.nombre} es de {de_falso}.",
        }
        n -= 1
        if n == 0:
            return


# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--por-tipo", type=int, default=30, help="preguntas nuevas por tipo y dificultad")
    args = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)

    with conectar() as conn:
        ejecucion = iniciar_ejecucion(conn, PASO)
        try:
            jug, clubes, paises, liga_de = cargar(conn)
            elegibles = [j for j in jug.values() if j.fechas_completas()]
            print(f"{len(jug)} jugadores en la base; {len(elegibles)} con fechas en todos sus clubes.")

            # Pasos de jugadores elegibles por club (para épocas y compañeros)
            por_club = defaultdict(list)
            for j in elegibles:
                for p in j.pasos:
                    por_club[p.club].append((j.qid, p))
            comp = {j.qid: companeros(j, por_club) for j in elegibles}
            ctx = (jug, clubes, liga_de, por_club, comp)
            dt = titulos.cargar(conn)
            print(f"Títulos: {len(dt.leidos)} jugadores con palmarés leído de Wikipedia; "
                  f"competiciones relevantes encontradas: {sorted(dt.nombre_familia)}")

            def valida(p: dict) -> bool:
                if p["tipo"] in ("ganadores_de_titulo", "equipos_campeones", "titulos_de_jugador"):
                    return titulos.es_valida(p, dt)
                return es_valida(p, jug)

            # 1) Revalidar lo que ya está guardado
            invalidas = [id_ for id_, tipo, prot, ops in conn.execute(
                "select id, tipo, protagonista, opciones from dato_falso_preguntas")
                if not valida({"tipo": tipo, "protagonista": prot, "opciones": ops})]
            if invalidas:
                conn.execute("delete from dato_falso_preguntas where id = any(%s)", (invalidas,))
            conn.commit()
            print(f"Revalidación: {len(invalidas)} preguntas guardadas ya no eran correctas y se borraron.")

            # 2) Generar nuevas
            rng = random.Random(HOY.toordinal())
            nuevas, rechazadas = 0, 0
            conteo = defaultdict(int)
            for dif in DIFICULTADES:
                for gen in (
                    gen_clubes_de_jugador(elegibles, dif, ctx, rng, args.por_tipo),
                    gen_jugadores_de_club(elegibles, dif, ctx, rng, args.por_tipo),
                    gen_jugadores_de_pais(elegibles, dif, ctx, rng, args.por_tipo, paises),
                    titulos.gen_ganadores_de_titulo(dt, dif, rng, args.por_tipo),
                    titulos.gen_equipos_campeones(dt, dif, rng, max(args.por_tipo // 3, 4)),
                    titulos.gen_titulos_de_jugador(dt, dif, rng, args.por_tipo),
                ):
                    for p in gen:
                        if not valida(p):   # doble verificación antes de guardar
                            rechazadas += 1
                            continue
                        r = conn.execute(
                            """insert into dato_falso_preguntas (clave, tipo, dificultad, afirmacion, protagonista,
                                 opciones, explicacion, ejecucion_id) values (%s, %s, %s, %s, %s, %s, %s, %s)
                               on conflict (clave) do nothing""",
                            (p["clave"], p["tipo"], p["dificultad"], p["afirmacion"], Jsonb(p["protagonista"]),
                             Jsonb(p["opciones"]), p["explicacion"], ejecucion),
                        )
                        if r.rowcount:
                            nuevas += 1
                            conteo[(p["tipo"], dif)] += 1
            conn.commit()
            total = dict(conn.execute(
                "select dificultad, count(*) from dato_falso_preguntas group by dificultad").fetchall())
            resumen = {"nuevas": nuevas, "borradas": len(invalidas), "rechazadas": rechazadas,
                       "total_por_dificultad": total,
                       "nuevas_por_tipo": {f"{t}/{d}": n for (t, d), n in conteo.items()}}
        except Exception as e:
            conn.rollback()
            terminar_ejecucion(conn, ejecucion, "error", {"error": str(e)[:500]})
            raise
        terminar_ejecucion(conn, ejecucion, "ok", resumen)

    print("\n=== Reporte: Dato Falso Futbolero ===")
    print(f"Preguntas nuevas: {nuevas} | borradas por revalidación: {len(invalidas)} | "
          f"rechazadas en la verificación final: {rechazadas}")
    for (t, d), n in sorted(conteo.items()):
        print(f"  {t:<22} {d:<11} {n}")
    print(f"Total guardado por dificultad: {total}")


if __name__ == "__main__":
    main()
