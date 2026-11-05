"""Paso 6: quién participó en cada Mundial, Eurocopa y Copa América (Wikidata P1344).

Solo se guardan jugadores que están en nuestra base y ediciones reales (con campeón,
guardadas en el paso 5). Se puede correr muchas veces: reemplaza los datos por los actuales.
Uso: pipeline/.venv/bin/python pipeline/paso6_participaciones.py
"""

from __future__ import annotations

import sys
from collections import Counter

import wikidata as wd
from db import conectar

TORNEOS = ("FIFA World Cup", "UEFA European Championship", "Copa América")


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)
    with conectar() as conn:
        ediciones = {q: (c, a, n) for q, c, a, n in conn.execute(
            """select e.qid, e.competicion_qid, e.anio, k.nombre from ediciones e
               join competiciones k on k.qid = e.competicion_qid
               where k.articulo_en = any(%s) and e.campeon_qid is not null""", (list(TORNEOS),))}
        jugadores = {r[0] for r in conn.execute("select qid from jugadores")}
        conn.commit()
    print(f"Consultando participantes de {len(ediciones)} ediciones…")

    filas = []
    lista = sorted(ediciones)
    for i in range(0, len(lista), 25):
        valores = " ".join("wd:" + q for q in lista[i : i + 25])
        for f in wd.sparql(f"SELECT ?j ?ed WHERE {{ VALUES ?ed {{ {valores} }} ?j wdt:P1344 ?ed . }}"):
            j, ed = wd.qid(f["j"]), wd.qid(f["ed"])
            if j in jugadores:
                filas.append((j, ed, ediciones[ed][0], ediciones[ed][1]))
    filas = list({(f[0], f[1]): f for f in filas}.values())

    with conectar() as conn:
        with conn.transaction():
            conn.execute("delete from participaciones")
            conn.cursor().executemany(
                "insert into participaciones (jugador_qid, edicion_qid, competicion_qid, anio) values (%s, %s, %s, %s)",
                filas,
            )
    por_torneo = Counter(ediciones[ed][2] for _, ed, _, _ in filas)
    print("\n=== Reporte del paso 6: participaciones ===")
    for nombre, n in por_torneo.most_common():
        print(f"  {nombre:<30} {n} participaciones de jugadores de la base")


if __name__ == "__main__":
    main()
