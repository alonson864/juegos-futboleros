"""Genera puzzles de Conexiones a partir de la base (no inventa datos).

Cada puzzle tiene 4 grupos de 4 jugadores. Las categorías salen de la base:
  - "Jugaron en {club}"
  - "Jugaron en {club A} y en {club B}"
  - "Jugaron por la selección de {país}"

Reglas que se verifican antes de guardar un puzzle:
  - Hay exactamente UNA forma de repartir los 16 jugadores en las 4 categorías
    (se prueban todas las combinaciones posibles).
  - Al menos un jugador "trampa" cumple también la categoría de otro grupo.
  - Al menos una categoría es latinoamericana (clubes o selecciones de Argentina/Perú).
  - No se repiten categorías usadas en los últimos 20 puzzles.

Se puede correr muchas veces: no toca los días que ya tienen puzzle (salvo --regenerar).
Uso: pipeline/.venv/bin/python pipeline/generar_conexiones.py [--desde AAAA-MM-DD] [--dias 30] [--regenerar]
"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from itertools import combinations

from psycopg.types.json import Jsonb

from db import conectar, iniciar_ejecucion, terminar_ejecucion

PASO = "generar_conexiones"
POPULARIDAD_MINIMA = 25      # Wikipedias: solo jugadores bastante conocidos
MIEMBROS_MINIMOS = 6         # una categoría necesita al menos esta cantidad de jugadores
PAISES_LATAM = ("Argentina", "Perú")  # países de ligas.json considerados latinoamericanos
VENTANA_SIN_REPETIR = 20


@dataclass
class Categoria:
    clave: str
    nombre: str
    tipo: str            # 'club' | 'par' | 'seleccion'
    latam: bool
    miembros: set[str] = field(default_factory=set)


def cargar(conn):
    jugadores = {q: (n, p) for q, n, p in conn.execute(
        "select qid, nombre, popularidad from jugadores_final where popularidad >= %s",
        (POPULARIDAD_MINIMA,))}
    pasos = conn.execute(
        """select p.jugador_qid, c.qid, c.nombre, c.tipo, c.pais_qid
           from pasos_por_club_final p join clubes_final c on c.qid = p.club_qid
           where c.tipo in ('club', 'seleccion')""").fetchall()
    paises = dict(conn.execute("select qid, nombre from paises").fetchall())
    latam = {r[0] for r in conn.execute(
        """select distinct c.pais_qid from clubes c join clubes_ligas cl on cl.club_qid = c.qid
           join ligas l on l.qid = cl.liga_qid where l.pais = any(%s) and c.pais_qid is not null""",
        (list(PAISES_LATAM),))}
    usadas = [r[0] for r in conn.execute(
        "select g->>'clave' from (select grupos from conexiones_puzzles order by fecha desc limit %s) p, "
        "jsonb_array_elements(p.grupos) g", (VENTANA_SIN_REPETIR,))]
    existentes = {r[0] for r in conn.execute("select fecha from conexiones_puzzles")}
    conn.commit()
    return jugadores, pasos, paises, latam, set(usadas), existentes


def armar_categorias(jugadores, pasos, paises, latam) -> list[Categoria]:
    cats: dict[str, Categoria] = {}
    for jug, club, nombre, tipo, pais in pasos:
        if jug not in jugadores:
            continue
        if tipo == "club":
            c = cats.setdefault(f"club:{club}", Categoria(f"club:{club}", f"Jugaron en {nombre}",
                                                         "club", pais in latam))
        else:
            if not pais or pais not in paises:
                continue
            c = cats.setdefault(f"sel:{pais}", Categoria(f"sel:{pais}",
                                                        f"Jugaron por la selección de {paises[pais]}",
                                                        "seleccion", pais in latam))
        c.miembros.add(jug)
    simples = [c for c in cats.values() if len(c.miembros) >= MIEMBROS_MINIMOS]

    # Pares de clubes con suficientes jugadores en común (solo entre los clubes más grandes)
    clubes = sorted((c for c in simples if c.tipo == "club"), key=lambda c: -len(c.miembros))[:150]
    pares = []
    for a, b in combinations(clubes, 2):
        comunes = a.miembros & b.miembros
        if len(comunes) >= MIEMBROS_MINIMOS:
            nombre_b = b.nombre.removeprefix("Jugaron en ")
            pares.append(Categoria(f"par:{a.clave}|{b.clave}", f"{a.nombre} y en {nombre_b}", "par",
                                   a.latam or b.latam, comunes))
    return simples + pares


def soluciones(jugs: list[str], cats: list[Categoria], tope: int = 2) -> int:
    """Cuántas formas hay de repartir los 16 jugadores en las 4 categorías (4 por categoría)."""
    cupos = [4] * len(cats)
    opciones = [[i for i, c in enumerate(cats) if j in c.miembros] for j in jugs]
    orden = sorted(range(len(jugs)), key=lambda k: len(opciones[k]))
    cuenta = 0

    def probar(k: int) -> None:
        nonlocal cuenta
        if cuenta >= tope:
            return
        if k == len(orden):
            cuenta += 1
            return
        for i in opciones[orden[k]]:
            if cupos[i]:
                cupos[i] -= 1
                probar(k + 1)
                cupos[i] += 1

    probar(0)
    return cuenta


def elegir(pool: list[str], n: int, jugadores, rng: random.Random) -> list[str] | None:
    if len(pool) < n:
        return None
    # Preferimos jugadores conocidos, pero con variedad: se elige al azar entre los más populares
    ordenados = sorted(pool, key=lambda q: -jugadores[q][1])[: max(n * 3, 10)]
    return rng.sample(ordenados, n)


def intentar(cats: list[Categoria], jugadores, rng: random.Random, usadas: set[str]):
    disponibles = [c for c in cats if c.clave not in usadas]
    for _ in range(3000):
        primera = rng.choice([c for c in disponibles if c.latam] or disponibles)
        elegidas = [primera]
        while len(elegidas) < 4:
            # Preferir categorías que compartan algún jugador con las ya elegidas (para la trampa),
            # pero que no se parezcan demasiado.
            vecinas = [c for c in disponibles if c not in elegidas
                       and any(c.miembros & e.miembros for e in elegidas)
                       and all(len(c.miembros & e.miembros) <= len(c.miembros) / 2 for e in elegidas)]
            elegidas.append(rng.choice(vecinas or [c for c in disponibles if c not in elegidas]))
        if not any(c.latam for c in elegidas):
            continue

        todos = set().union(*(c.miembros for c in elegidas))
        exclusivos = {id(c): [j for j in c.miembros
                              if sum(j in d.miembros for d in elegidas) == 1] for c in elegidas}
        dobles = [(j, c, d) for c in elegidas for d in elegidas if c is not d
                  for j in c.miembros & d.miembros
                  if sum(j in e.miembros for e in elegidas) == 2]
        if not dobles:
            continue
        trampa, grupo_trampa, otra = rng.choice(dobles)

        grupos = []
        for c in elegidas:
            n = 3 if c is grupo_trampa else 4
            elegidos = elegir(exclusivos[id(c)], n, jugadores, rng)
            if elegidos is None:
                break
            grupos.append((c, elegidos + ([trampa] if c is grupo_trampa else [])))
        else:
            jugs = [j for _, js in grupos for j in js]
            if len(set(jugs)) == 16 and todos and soluciones(jugs, elegidas) == 1:
                return grupos, (trampa, otra)
    return None


def dificultades(grupos, jugadores) -> list[int]:
    base = {"seleccion": 0.0, "club": 1.0, "par": 2.5}
    puntajes = []
    for c, js in grupos:
        fama = sum(jugadores[j][1] for j in js) / len(js)
        puntajes.append(base[c.tipo] - fama / 100)
    orden = sorted(range(4), key=lambda i: puntajes[i])
    dif = [0] * 4
    for rango, i in enumerate(orden, 1):
        dif[i] = rango
    return dif


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", type=date.fromisoformat, default=date.today())
    ap.add_argument("--dias", type=int, default=30)
    ap.add_argument("--regenerar", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)

    with conectar() as conn:
        ejecucion = iniciar_ejecucion(conn, PASO)
        try:
            jugadores, pasos, paises, latam, usadas, existentes = cargar(conn)
            cats = armar_categorias(jugadores, pasos, paises, latam)
            print(f"{len(jugadores)} jugadores con {POPULARIDAD_MINIMA}+ Wikipedias, {len(cats)} categorías posibles "
                  f"({sum(c.latam for c in cats)} latinoamericanas).")
            creados, sin_lograr = [], []
            for d in range(args.dias):
                fecha = args.desde + timedelta(days=d)
                if fecha in existentes and not args.regenerar:
                    continue
                rng = random.Random(fecha.toordinal())
                r = intentar(cats, jugadores, rng, usadas)
                if not r:
                    sin_lograr.append(fecha.isoformat())
                    continue
                grupos, (trampa, otra) = r
                difs = dificultades(grupos, jugadores)
                datos = [{
                    "clave": c.clave,
                    "categoria": c.nombre,
                    "dificultad": dif,
                    "jugadores": [jugadores[j][0] for j in js],
                    "jugadores_qid": js,
                } for (c, js), dif in sorted(zip(grupos, difs), key=lambda x: x[1])]
                trampas = [f"{jugadores[trampa][0]} también cumple «{otra.nombre}»."]
                conn.execute(
                    """insert into conexiones_puzzles (fecha, grupos, trampas, ejecucion_id) values (%s, %s, %s, %s)
                       on conflict (fecha) do update set grupos = excluded.grupos, trampas = excluded.trampas,
                         generado_en = now(), ejecucion_id = excluded.ejecucion_id""",
                    (fecha, Jsonb(datos), Jsonb(trampas), ejecucion),
                )
                conn.commit()
                usadas |= {c.clave for c, _ in grupos}
                creados.append(fecha.isoformat())
                print(f"  {fecha}: " + " | ".join(g["categoria"] for g in datos))
            resumen = {"creados": len(creados), "sin_lograr": sin_lograr, "categorias": len(cats)}
        except Exception as e:
            conn.rollback()
            terminar_ejecucion(conn, ejecucion, "error", {"error": str(e)[:500]})
            raise
        terminar_ejecucion(conn, ejecucion, "ok", resumen)
    print(f"\nPuzzles creados: {len(creados)}. Días sin lograr un puzzle válido: {len(sin_lograr)}.")


if __name__ == "__main__":
    main()
