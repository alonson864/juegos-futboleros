"""Genera las rondas del juego "Buscaminas" (lee SOLO de la base).

Cada ronda: una categoría y 16 jugadores, 12 que la cumplen y 4 impostores.
Los impostores deben ser difíciles de detectar (misma selección y época, mismo club,
misma liga…), y SIEMPRE seguros: solo pueden ser jugadores cuyo palmarés leímos de
Wikipedia y que no aparecen en ningún registro de la categoría.

Categorías:
  campeon_seleccion  "Campeones del mundo con Argentina en 2022" / Eurocopa / Copa América
  premio             "Ganaron el Balón de Oro" / "Ganaron la Bota de Oro"
  champions_club     "Ganaron la Champions con el Real Madrid"
  champions_dos      "Ganaron la Champions con dos clubes distintos"
  club               "Jugaron en el Arsenal" (impostores: figuras de rivales del mismo país)

De cada categoría se guardan varias versiones (otros 12 + 4), para no repetir.
Uso: pipeline/.venv/bin/python pipeline/generar_buscaminas.py
"""

from __future__ import annotations

import random
import sys
from collections import defaultdict
from datetime import date

from psycopg.types.json import Jsonb

import dato_falso_titulos as titulos
import reconocidos
from db import conectar, iniciar_ejecucion, terminar_ejecucion
from generar_ultimo_en_pie import gentilicio_plural
from nombres import club_corto

PASO = "generar_buscaminas"
VERSIONES = 3          # versiones distintas de cada categoría
CUMPLEN, IMPOSTORES = 12, 4
FAMOSOS = 2500         # puesto máximo de fama de los jugadores que se muestran

NOMBRE_TORNEO = {"mundial": "Campeones del mundo con {pais} en {anio}",
                 "eurocopa": "Campeones de la Eurocopa {anio} con {pais}",
                 "copa_america": "Campeones de la Copa América {anio} con {pais}"}


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
    print("\n=== Reporte: Buscaminas ===")
    for dif in ("facil", "intermedio", "dificil"):
        print(f"  {dif:<11} {resumen['por_dificultad'].get(dif, 0)} rondas ({resumen['categorias'].get(dif, 0)} categorías)")
    for t, n in resumen["por_tipo"].items():
        print(f"    {t:<18} {n} categorías")


def correr(conn) -> dict:
    rng = random.Random(date.today().toordinal())
    rec = reconocidos.cargar(conn)
    fotos = reconocidos.fotos(conn)
    dt = titulos.cargar(conn)
    nombre = {q: n for q, (n, _, _) in dt.jugadores.items()}
    famoso = {j for j, r in rec.rango.items() if r <= FAMOSOS and j in nombre}

    # Todos los clubes de cada jugador en CUALQUIER registro (originales y corregidos), para la seguridad
    registros_club = defaultdict(set)
    for j, c in conn.execute("select jugador_qid, club_qid from pasos_por_club union "
                             "select jugador_qid, equipo_qid from carrera_wikipedia where equipo_qid is not null"):
        registros_club[j] |= {c} | rec.alias[c]
    # Participaciones (Wikidata) por torneo y año
    participo = defaultdict(set)   # (familia, año) -> jugadores
    for j, comp, anio in conn.execute("select jugador_qid, competicion_qid, anio from participaciones"):
        if comp in dt.familia_de:
            participo[(dt.familia_de[comp], anio)].add(j)
    periodos = defaultdict(list)   # jugador -> [(equipo, desde, hasta)]
    for j, e, ini, fin in conn.execute(
            """select p.jugador_qid, p.club_qid, extract(year from p.inicio)::int, extract(year from p.fin)::int
               from pasos_por_club_final p join clubes c on c.qid = p.club_qid where c.tipo = 'seleccion'"""):
        periodos[j].append((e, ini, fin))
    for j, e, ini, fin in conn.execute(
            "select jugador_qid, equipo_qid, desde, hasta from carrera_wikipedia where seleccion and equipo_qid is not null"):
        periodos[j].append((e, ini, fin))
    gentilicio = dict(conn.execute("select qid, gentilicio from paises").fetchall())
    nacionalidad = {q: set(n or []) for q, n in conn.execute("select qid, nacionalidades from jugadores_final")}
    conn.commit()

    def en_seleccion(j, equipos, anio, margen=2):
        """¿Jugó por esa selección cerca de ese año (± margen)? Misma camada: impostor creíble."""
        return any(e in equipos and ini and ini - margen <= anio <= (fin or date.today().year) + margen
                   for e, ini, fin in periodos[j])

    def selecciones_de(j):
        return {e for e in dt.equipos_de.get(j, ()) if dt.tipo_equipo.get(e) == "seleccion"}

    def mas_famosos(js, n):
        return sorted(js, key=lambda j: rec.rango.get(j, 10**9))[:n]

    cats: list[dict] = []

    def agregar(clave, titulo, dificultad, cumplen, impostores, explicacion):
        """Guarda VERSIONES rondas: 12 de los más famosos que cumplen + 4 impostores creíbles."""
        cumplen = [j for j in cumplen if j in famoso]
        impostores = [j for j in impostores if j in famoso and j not in cumplen]
        if len(cumplen) < CUMPLEN or len(impostores) < IMPOSTORES:
            return
        base_c = mas_famosos(cumplen, CUMPLEN + 6)
        base_i = mas_famosos(impostores, IMPOSTORES + 6)
        for v in range(VERSIONES):
            sc = rng.sample(base_c, CUMPLEN)
            si = rng.sample(base_i, IMPOSTORES)
            fichas = [{"qid": j, "nombre": nombre[j], "cumple": True, **({"foto": fotos[j]} if j in fotos else {})} for j in sc]
            fichas += [{"qid": j, "nombre": nombre[j], "cumple": False, **({"foto": fotos[j]} if j in fotos else {})} for j in si]
            rng.shuffle(fichas)
            cats.append({"clave": f"{clave}#{v}", "categoria": clave, "titulo": titulo, "dificultad": dificultad,
                         "fichas": fichas, "explicacion": explicacion})

    campeon_de = defaultdict(dict)   # familia -> año -> equipo campeón
    for fam, eqs in dt.campeones.items():
        for e, anios in eqs.items():
            for a in anios:
                campeon_de[fam][a] = e

    # 1) Planteles campeones con su selección (Mundial, Eurocopa, Copa América desde 1998)
    for fam in ("mundial", "eurocopa", "copa_america"):
        for anio, equipo in campeon_de[fam].items():
            if anio < 1998 or dt.tipo_equipo.get(equipo) != "seleccion":
                continue
            equipos = {equipo} | rec.alias[equipo]
            pais = dt.nombre_equipo.get(equipo, "")
            # Cumplen: SOLO quienes tienen ese título en su palmarés de Wikipedia (la participación de
            # Wikidata no distingue jugadores de entrenadores u otros integrantes de la delegación)
            cumplen = {j for j, ts in dt.titulos.items() if (fam, anio) in ts and selecciones_de(j) & equipos}
            # Impostores: jugaron por esa selección cerca de ese año, palmarés leído, sin ningún registro del título
            # y sin participación registrada en ese torneo
            impostores = {j for j in dt.leidos if j in nombre and en_seleccion(j, equipos, anio)
                          and j not in cumplen and not titulos.algun_registro(dt, j, fam, anio)
                          and j not in participo[(fam, anio)]}
            dif = "facil" if anio >= 2018 else "intermedio" if anio >= 2008 else "dificil"
            agregar(f"campeon:{fam}:{anio}", NOMBRE_TORNEO[fam].format(pais=pais, anio=anio), dif, cumplen, impostores,
                    f"Los impostores también jugaron por {pais} en esa época, pero no fueron campeones en {anio}.")

    # 2) Premios
    for fam, dif in (("balon_de_oro", "intermedio"), ("bota_de_oro", "dificil")):
        ganadores = {j for j, ts in dt.titulos.items() if j in nombre and any(f == fam for f, _ in ts)}
        # Impostores: cracks con títulos grandes (Champions o Mundial) que nunca lo ganaron
        grandes = {j for j, ts in dt.titulos.items() if any(f in ("champions", "mundial") for f, _ in ts)}
        impostores = {j for j in grandes & dt.leidos if j not in ganadores and not titulos.algun_registro(dt, j, fam)}
        agregar(f"premio:{fam}", f"Ganaron {titulos.TEXTO[fam][0]}", dif, ganadores, impostores,
                f"Los impostores ganaron títulos importantes, pero nunca {titulos.TEXTO[fam][0]}.")

    # 3) Champions con un club / con dos clubes
    anios_club = defaultdict(set)   # club -> años en que ganó la Champions
    for a, e in campeon_de["champions"].items():
        for x in {e} | rec.alias[e]:
            anios_club[x].add(a)
    gano_con = defaultdict(set)     # jugador -> clubes con los que ganó la Champions
    for j, ts in dt.titulos.items():
        for f, a in ts:
            if f == "champions":
                for e in dt.equipos_de.get(j, ()):
                    if a in anios_club.get(e, ()):
                        gano_con[j].add(min({e} | rec.alias[e]))
    for club in rec.clubes:
        equipos = {club} | rec.alias[club]
        if not any(anios_club.get(e) for e in equipos):
            continue
        nombre_club = club_corto(dt.nombre_equipo.get(club, club))
        cumplen = {j for j, cs in gano_con.items() if cs & {min(equipos)} or any(e in equipos for e in cs)}
        anios = set().union(*(anios_club.get(e, set()) for e in equipos))
        # Impostores: pasaron por el club pero no ganaron la Champions con él
        impostores = {j for j in dt.leidos if registros_club[j] & equipos and j not in cumplen
                      and not any(titulos.algun_registro(dt, j, "champions", a) for a in anios)}
        agregar(f"champions_club:{club}", f"Ganaron la Champions con el {nombre_club}", "intermedio",
                cumplen, impostores, f"Los impostores jugaron en el {nombre_club}, pero no ganaron la Champions con él.")

    dos = {j for j, cs in gano_con.items() if len(cs) >= 2}
    uno = {j for j, cs in gano_con.items() if len(cs) == 1}
    # Seguridad: si tiene Champions en años de varios clubes suyos según algún registro, no es impostor
    uno = {j for j in uno if j in dt.leidos}
    agregar("champions_dos", "Ganaron la Champions con dos clubes distintos", "dificil", dos, uno,
            "Los impostores ganaron la Champions, pero con un solo club.")

    # 4) Jugaron en un club grande (impostores: figuras de los otros grandes del mismo país)
    por_pais = defaultdict(set)
    for c, p in rec.clubes.items():
        por_pais[p].add(c)
    for club, pais in rec.clubes.items():
        equipos = {club} | rec.alias[club]
        nombre_club = club_corto(dt.nombre_equipo.get(club, club))
        cumplen = {j for j in nombre if dt.equipos_de.get(j, set()) & equipos}
        rivales = set().union(*({c} | rec.alias[c] for c in por_pais[pais] - {club}))
        impostores = {j for j in dt.leidos if dt.equipos_de.get(j, set()) & rivales and not registros_club[j] & equipos}
        agregar(f"club:{club}", f"Jugaron en el {nombre_club}", "facil", cumplen, impostores,
                f"Los impostores jugaron en otros grandes del mismo país, nunca en el {nombre_club}.")

    # 5) Nacionalidad + club grande (difícil): "Brasileños que jugaron en el Barcelona"
    #    Impostores: de la misma nacionalidad, jugaron en otro grande del mismo país, nunca en ese club
    pais_de_sel = dict(conn.execute("select qid, pais_qid from clubes where tipo = 'seleccion'").fetchall())
    conn.commit()
    naciones = {pais_de_sel[c] for c in rec.selecciones if pais_de_sel.get(c)}
    for club, pais_liga in rec.clubes.items():
        equipos = {club} | rec.alias[club]
        nombre_club = club_corto(dt.nombre_equipo.get(club, club))
        rivales = set().union(*({c} | rec.alias[c] for c in por_pais[pais_liga] - {club}))
        for nac in naciones:
            plural = gentilicio_plural(gentilicio.get(nac))
            if not plural:
                continue
            cumplen = {j for j in nombre if nac in nacionalidad.get(j, ()) and dt.equipos_de.get(j, set()) & equipos}
            impostores = {j for j in dt.leidos if nac in nacionalidad.get(j, ()) and dt.equipos_de.get(j, set()) & rivales
                          and not registros_club[j] & equipos}
            agregar(f"nacion_club:{nac}:{club}", f"{plural} que jugaron en el {nombre_club}", "dificil",
                    cumplen, impostores,
                    f"Los impostores también son {plural.lower()} y jugaron en rivales del {nombre_club}, pero nunca ahí.")

    with conn.transaction():
        conn.execute("delete from buscaminas_rondas")
        conn.cursor().executemany(
            """insert into buscaminas_rondas (clave, categoria, titulo, dificultad, fichas, explicacion)
               values (%s, %s, %s, %s, %s, %s)""",
            [(c["clave"], c["categoria"], c["titulo"], c["dificultad"], Jsonb(c["fichas"]), c["explicacion"]) for c in cats],
        )
    por_dif, cat_dif, por_tipo = defaultdict(int), defaultdict(set), defaultdict(set)
    for c in cats:
        por_dif[c["dificultad"]] += 1
        cat_dif[c["dificultad"]].add(c["categoria"])
        por_tipo[c["categoria"].split(":")[0]].add(c["categoria"])
    return {"por_dificultad": dict(por_dif), "categorias": {d: len(v) for d, v in cat_dif.items()},
            "por_tipo": {t: len(v) for t, v in por_tipo.items()}}


if __name__ == "__main__":
    main()
