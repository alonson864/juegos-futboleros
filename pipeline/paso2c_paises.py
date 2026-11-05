"""Paso 2c: continente y gentilicio de cada país (Wikidata), para categorías por origen.
Uso: pipeline/.venv/bin/python pipeline/paso2c_paises.py
"""

from __future__ import annotations

import sys

import wikidata as wd
from db import conectar


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)
    with conectar() as conn:
        paises = [r[0] for r in conn.execute("select qid from paises")]
        conn.commit()
    datos, continentes = {}, set()
    for e in wd.entidades(paises, props="claims", idiomas="es"):
        cont = wd.valores(e, "P30")
        gentilicio = None
        for st in e.get("claims", {}).get("P1549", []):
            v = st.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            if isinstance(v, dict) and v.get("language") == "es" and st.get("rank") != "deprecated":
                gentilicio = v.get("text")
                break
        datos[e["id"]] = (cont[0] if len(cont) == 1 else None, gentilicio)
        continentes |= {c for c, _ in [datos[e["id"]]] if c}
    nombres = {e["id"]: wd.etiqueta(e) for e in wd.entidades(continentes, props="labels", idiomas="es")}
    with conectar() as conn:
        conn.cursor().executemany(
            "update paises set continente_qid = %s, continente = %s, gentilicio = %s where qid = %s",
            [(c, nombres.get(c), g, q) for q, (c, g) in datos.items()],
        )
        conn.commit()
        print("Países por continente:", conn.execute(
            "select continente, count(*) from paises group by 1 order by 2 desc").fetchall())
        print("Con gentilicio:", conn.execute("select count(*) from paises where gentilicio is not null").fetchone()[0],
              "de", len(paises))
        print("Ejemplos:", conn.execute(
            "select nombre, gentilicio, continente from paises where nombre in "
            "('Argentina','Brasil','Perú','Francia','Inglaterra','Reino Unido','Países Bajos','Costa de Marfil')").fetchall())


if __name__ == "__main__":
    main()
