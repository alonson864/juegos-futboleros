"""Paso 8: control de calidad de los pasos por clubes (Wikidata).

Marca como sospechoso (y excluye con la tabla de correcciones, con su motivo) un paso
por un CLUB cuando:
  1. Tiene fechas imposibles: empieza antes de que el jugador naciera o termina en el
     futuro (por ejemplo, "Real Madrid de 1930 a 2930" en un jugador nacido en 2003).
  2. Contradice a Wikipedia: el jugador tiene su carrera leída de Wikipedia (paso 4)
     y ese club no aparece en ella (tampoco sus fichas equivalentes).

No borra datos: solo agrega correcciones "_excluir" marcadas como automáticas, que
se pueden revisar y quitar. Las correcciones manuales nunca se tocan.
Uso: pipeline/.venv/bin/python pipeline/paso8_calidad.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date

from db import conectar

MARCA = "[automático]"


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)
    hoy = date.today()
    with conectar() as conn:
        alias = defaultdict(set)
        for a, c in conn.execute("select qid, club_qid from clubes_alias"):
            alias[a].add(c)
            alias[c].add(a)
        nacimiento = dict(conn.execute("select qid, fecha_nacimiento from jugadores").fetchall())
        carrera = defaultdict(set)
        for j, eq in conn.execute("select jugador_qid, equipo_qid from carrera_wikipedia where equipo_qid is not null"):
            carrera[j] |= {eq} | alias[eq]
        pasos = conn.execute(
            """select p.id_wikidata, p.jugador_qid, p.club_qid, p.inicio, p.fin, c.nombre, j.nombre
               from pasos_por_club p join clubes c on c.qid = p.club_qid join jugadores j on j.qid = p.jugador_qid
               where c.tipo = 'club'""").fetchall()

        sospechosos = []
        for id_, j, club, ini, fin, nclub, njug in pasos:
            motivo = None
            nac = nacimiento.get(j)
            # (los pasos de juveniles en la ficha del club son normales: solo es imposible antes de nacer)
            if ini and nac and ini.year < nac.year:
                motivo = f"empieza antes de que naciera ({ini.year}, nació en {nac.year})"
            elif fin and fin.year > hoy.year + 1:
                motivo = f"fecha de fin en el futuro ({fin.year})"
            elif j in carrera and not ({club} | alias[club]) & carrera[j]:
                motivo = "no figura en su carrera según Wikipedia"
            if motivo:
                sospechosos.append((id_, f"{MARCA} {njug} en {nclub}: {motivo}."))

        with conn.transaction():
            # Se rehacen solo las automáticas (las manuales no se tocan)
            conn.execute("delete from correcciones where tabla = 'pasos_por_club' and campo = '_excluir' "
                         "and motivo like %s", (MARCA + "%",))
            conn.cursor().executemany(
                """insert into correcciones (tabla, registro, campo, valor, motivo) values ('pasos_por_club', %s, '_excluir', null, %s)
                   on conflict (tabla, registro, campo) do nothing""",
                sospechosos,
            )
    por_motivo = defaultdict(int)
    for _, m in sospechosos:
        por_motivo[m.split(": ", 1)[1].split(" (")[0].rstrip(".")] += 1
    print("=== Reporte del paso 8: control de calidad ===")
    print(f"Pasos por clubes revisados: {len(pasos)} | excluidos por sospechosos: {len(sospechosos)}")
    for m, n in sorted(por_motivo.items(), key=lambda x: -x[1]):
        print(f"  {m}: {n}")
    print("Ejemplos:")
    for _, m in sospechosos[:12]:
        print("  ", m)


if __name__ == "__main__":
    main()
