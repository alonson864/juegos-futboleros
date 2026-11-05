"""Paso 2b: corrige nombres de jugadores sin bajar todo de nuevo.

- Jugadores cuyo nombre quedó como código (Q123…): busca su nombre en más idiomas.
- Nombres legales largos ("Fernando Luiz Rosa") -> nombre futbolístico ("Fernandinho"),
  usando el título del artículo de Wikipedia en inglés.
Las correcciones manuales siguen teniendo prioridad (la vista jugadores_final las aplica).
Uso: pipeline/.venv/bin/python pipeline/paso2b_nombres.py
"""

from __future__ import annotations

import re
import sys

import wikidata as wd
from db import conectar
from nombres import normalizar


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)
    with conectar() as conn:
        actuales = dict(conn.execute("select qid, nombre from jugadores").fetchall())
        conn.commit()
    print(f"Revisando nombres de {len(actuales)} jugadores…")
    cambios, busquedas = {}, {}
    for e in wd.entidades(list(actuales), props="labels|aliases|sitelinks", idiomas="es|en|pt|it|fr|de"):
        enwiki = e.get("sitelinks", {}).get("enwiki", {}).get("title")
        nuevo = wd.nombre_futbolistico(wd.etiqueta(e), enwiki)
        if nuevo and nuevo != actuales.get(e["id"]):
            cambios[e["id"]] = nuevo
        # Texto de búsqueda: nombre, nombres en otros idiomas, apodos y título en Wikipedia
        variantes = {nuevo or "", re.sub(r"\s*\(.*\)$", "", enwiki or "")}
        variantes |= {v["value"] for v in e.get("labels", {}).values()}
        variantes |= {a["value"] for lista in e.get("aliases", {}).values() for a in lista}
        busquedas[e["id"]] = " | ".join(sorted({normalizar(v) for v in variantes if v}))
    with conectar() as conn:
        conn.cursor().executemany(
            "update jugadores set nombre = %s, actualizado_en = now() where qid = %s",
            [(n, q) for q, n in cambios.items()],
        )
        conn.cursor().executemany(
            "update jugadores set busqueda = %s where qid = %s and busqueda is distinct from %s",
            [(b, q, b) for q, b in busquedas.items()],
        )
        sin_nombre = conn.execute("select count(*) from jugadores where nombre ~ '^Q[0-9]+$'").fetchone()[0]
        conn.commit()
    print(f"Nombres corregidos: {len(cambios)}. Siguen sin nombre: {sin_nombre}.")
    for q, n in list(cambios.items())[:12]:
        print(f"  {actuales[q]}  ->  {n}")


if __name__ == "__main__":
    main()
