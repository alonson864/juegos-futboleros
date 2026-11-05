"""Paso 7: fama real de cada jugador = visitas a su artículo de Wikipedia (inglés + español)
en los últimos 60 días, según la API de Wikipedia (de a 50 artículos por pedido).

Mide mejor que "en cuántas Wikipedias tiene artículo": hay jugadores con artículos
creados en masa en decenas de Wikipedias pequeñas que casi nadie visita.
Uso: pipeline/.venv/bin/python pipeline/paso7_fama.py
"""

from __future__ import annotations

import sys
import time
from datetime import date

import wikidata as wd
from db import conectar



def periodo() -> tuple[str, str]:  # (se mantiene para el reporte)
    hoy = date.today()
    fin = date(hoy.year, hoy.month, 1)                       # hasta el mes pasado completo
    inicio = date(fin.year - 1, fin.month, 1)
    return inicio.strftime("%Y%m%d"), (date.fromordinal(fin.toordinal() - 1)).strftime("%Y%m%d")


def titulos(qids: list[str]) -> dict[str, dict[str, str]]:
    """qid -> {"en": título, "es": título}, con consultas SPARQL de a 400 jugadores."""
    from urllib.parse import unquote
    salida: dict[str, dict[str, str]] = {}
    for i in range(0, len(qids), 400):
        valores = " ".join("wd:" + q for q in qids[i : i + 400])
        for f in wd.sparql(f"""
            SELECT ?j ?art WHERE {{
              VALUES ?j {{ {valores} }}
              VALUES ?wiki {{ <https://en.wikipedia.org/> <https://es.wikipedia.org/> }}
              ?art schema:about ?j ; schema:isPartOf ?wiki .
            }}"""):
            idioma = "en" if "//en." in f["art"] else "es"
            titulo = unquote(f["art"].rsplit("/wiki/", 1)[-1]).replace("_", " ")
            salida.setdefault(wd.qid(f["j"]), {})[idioma] = titulo
        print(f"  títulos: {min(i + 400, len(qids))}/{len(qids)}", flush=True)
    return salida


def visitas_por_lotes(idioma: str, lista: list[str]) -> dict[str, int]:
    """título -> visitas de los últimos 60 días, de a 50 artículos por pedido (API de Wikipedia).

    Un pedido a la vez y respetando las pausas que pida el servidor. Si un lote falla, se
    lanza un error (no se anota 0, para no guardar datos falsos).
    """
    url = f"https://{idioma}.wikipedia.org/w/api.php"
    salida: dict[str, int] = {}
    for i in range(0, len(lista), 50):
        lote = lista[i : i + 50]
        params = {
            "action": "query", "titles": "|".join(lote), "prop": "pageviews", "pvipdays": 60,
            "redirects": 1, "format": "json", "formatversion": 2,
        }
        destino = {t: t for t in lote}
        redir: dict[str, str] = {}
        por_titulo: dict[str, int] = {}
        # La API devuelve las visitas por partes: hay que seguir "continue" hasta el final
        while True:
            datos = wd._pedir("GET", url, params=params).json()
            q = datos.get("query", {})
            for n in q.get("normalized", []):
                destino[n["from"]] = n["to"]
            redir.update({r["from"]: r["to"] for r in q.get("redirects", [])})
            for p in q.get("pages", []):
                if p.get("pageviews"):
                    por_titulo[p["title"]] = sum(v or 0 for v in p["pageviews"].values())
            if "continue" not in datos:
                break
            params = {**params, **datos["continue"]}
        for t in lote:
            final = redir.get(destino[t], destino[t])
            salida[t] = por_titulo.get(final, 0)
        if (i // 50) % 50 == 0:
            print(f"  {idioma}: {min(i + 50, len(lista))}/{len(lista)} artículos", flush=True)
    return salida


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)
    with conectar() as conn:
        qids = [r[0] for r in conn.execute("select qid from jugadores order by qid")]
        conn.commit()
    desde, hasta = periodo()
    print(f"Fama de {len(qids)} jugadores (visitas de los últimos 60 días en Wikipedia en inglés y español)…")
    tit = titulos(qids)

    total: dict[str, int] = {q: 0 for q in qids}
    for idioma in ("en", "es"):
        por_jugador = {q: ts[idioma] for q, ts in tit.items() if idioma in ts}
        vistas = visitas_por_lotes(idioma, sorted(set(por_jugador.values())))
        for q, t in por_jugador.items():
            total[q] += vistas.get(t, 0)

    with conectar() as conn:
        conn.cursor().executemany("update jugadores set visitas = %s where qid = %s",
                                  [(v, q) for q, v in total.items()])
        conn.commit()
        print("\n=== Reporte del paso 7: fama ===")
        print("Los 15 más visitados:", ", ".join(r[0] for r in conn.execute(
            "select nombre from jugadores order by visitas desc nulls last limit 15")))
        for n in ("Paolo Guerrero", "Percy Liza", "Claudio Pizarro", "Teófilo Cubillas"):
            print(f"  {n}: {conn.execute('select visitas from jugadores where nombre=%s', (n,)).fetchone()}")


if __name__ == "__main__":
    main()
