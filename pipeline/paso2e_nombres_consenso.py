"""Paso 2e: corrige nombres cuando Wikipedia en inglés y en español coinciden y nuestro
nombre (la etiqueta en español de Wikidata) es distinto.

Las etiquetas de Wikidata a veces tienen vandalismo ("Sancho Panza" por Jadon Sancho,
"El Arrebato" por Guillermo Ochoa) o errores ("Jorge Alba" por Jordi Alba). Si los títulos
de los artículos en inglés y en español dicen lo mismo, ese es el nombre por el que se
conoce al jugador. Se corre DESPUÉS de los pasos 2b y 2d.
Las correcciones manuales siguen teniendo prioridad (jugadores_final).
Uso: pipeline/.venv/bin/python pipeline/paso2e_nombres_consenso.py
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from urllib.parse import unquote

import wikidata as wd
from db import conectar
from nombres import normalizar


def limpio(url: str) -> str:
    return re.sub(r"\s*\(.*\)$", "", unquote(url.rsplit("/wiki/", 1)[-1]).replace("_", " ")).strip()


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)
    with conectar() as conn:
        nombres = dict(conn.execute("select qid, nombre from jugadores").fetchall())
        conn.commit()
    qids = sorted(nombres)
    titulos: dict[str, dict[str, str]] = {}
    for i in range(0, len(qids), 400):
        valores = " ".join("wd:" + q for q in qids[i : i + 400])
        for f in wd.sparql(f"""
            SELECT ?j ?art WHERE {{
              VALUES ?j {{ {valores} }}
              VALUES ?wiki {{ <https://en.wikipedia.org/> <https://es.wikipedia.org/> }}
              ?art schema:about ?j ; schema:isPartOf ?wiki .
            }}"""):
            titulos.setdefault(wd.qid(f["j"]), {})["en" if "//en." in f["art"] else "es"] = limpio(f["art"])
        print(f"  títulos: {min(i + 400, len(qids))}/{len(qids)}", flush=True)

    candidatos = {q: t["en"] for q, t in titulos.items()
                  if "en" in t and "es" in t and normalizar(t["en"]) == normalizar(t["es"])
                  and normalizar(t["en"]) != normalizar(nombres[q])}
    # Un nombre de una sola palabra que usan varios jugadores no se aplica (sería ambiguo)
    cuenta = Counter(normalizar(n) for n in list(nombres.values()) + list(candidatos.values()))
    cambios = {q: (nombres[q], n) for q, n in candidatos.items()
               if not (" " not in n and cuenta[normalizar(n)] > 1)}

    with conectar() as conn:
        conn.cursor().executemany("update jugadores set nombre = %s, actualizado_en = now() where qid = %s",
                                  [(n, q) for q, (_, n) in cambios.items()])
        conn.commit()
    print(f"\nNombres corregidos por consenso de Wikipedia en inglés y en español: {len(cambios)}")
    for a, n in list(cambios.values())[:40]:
        print(f"  {a}  ->  {n}")


if __name__ == "__main__":
    main()
