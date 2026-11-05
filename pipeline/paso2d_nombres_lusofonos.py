"""Paso 2d: nombres de brasileños y portugueses por el título de su artículo en Wikipedia
en inglés (el nombre por el que se los conoce), no el nombre legal.

No usa la etiqueta en inglés de Wikidata: a veces tiene vandalismo. Las correcciones
manuales siguen teniendo prioridad (jugadores_final).
Uso: pipeline/.venv/bin/python pipeline/paso2d_nombres_lusofonos.py
"""

from __future__ import annotations

import re
import sys
from collections import Counter

import wikidata as wd
from db import conectar
from nombres import nombre_lusofono, normalizar


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)
    with conectar() as conn:
        lusos = [r[0] for r in conn.execute("select qid from paises where nombre in ('Brasil', 'Portugal')")]
        jugadores = dict(conn.execute(
            "select qid, nombre from jugadores where nacionalidades && %s", (lusos,)).fetchall())
        conn.commit()
    print(f"Revisando {len(jugadores)} brasileños y portugueses…")
    titulos = {}
    for e in wd.entidades(list(jugadores), props="sitelinks", idiomas="en"):
        t = e.get("sitelinks", {}).get("enwiki", {}).get("title")
        if t:
            titulos[e["id"]] = t
    # Apodos de una palabra que usan varios jugadores (por ejemplo "Alex"): ambiguos
    cuenta = Counter(normalizar(re.sub(r"\s*\(.*\)$", "", t)) for t in titulos.values())
    repetidos = {k for k, n in cuenta.items() if n > 1 and " " not in k}

    cambios = {}
    for q, actual in jugadores.items():
        nuevo = nombre_lusofono(actual, titulos.get(q), repetidos)
        if nuevo != actual:
            cambios[q] = (actual, nuevo)
    with conectar() as conn:
        conn.cursor().executemany("update jugadores set nombre = %s, actualizado_en = now() where qid = %s",
                                  [(n, q) for q, (_, n) in cambios.items()])
        conn.commit()
    print(f"Nombres cambiados: {len(cambios)} (apodos ambiguos que no se usan: {len(repetidos)})")
    for a, n in list(cambios.values())[:30]:
        print(f"  {a}  ->  {n}")


if __name__ == "__main__":
    main()
