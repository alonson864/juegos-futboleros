"""Paso 9: listas de Wikipedia en inglés que usa el juego "Mayor o menor".

- Fichajes: tabla "Top 50 most expensive association football transfers" del artículo
  "List of most expensive association football transfers" (monto en millones de euros).
- Asistencias: tabla "Most assists (career)" de "Premier League records and statistics"
  (asistencias oficiales de la Premier League).

Se leen solo las celdas de las tablas y los enlaces a los artículos de cada jugador
(no se interpreta prosa). Cada vez se reemplaza la lista con la versión actual del artículo.
Contenido de Wikipedia: licencia CC BY-SA 4.0.
Uso: pipeline/.venv/bin/python pipeline/paso9_listas_wikipedia.py
"""

from __future__ import annotations

import re
import sys

import wikipedia as wp
from db import conectar, iniciar_ejecucion, terminar_ejecucion

PASO = "paso9_listas_wikipedia"
ART_FICHAJES = "List of most expensive association football transfers"
ART_ASISTENCIAS = "Premier League records and statistics"

_ENLACE = re.compile(r"\[\[([^\[\]|#]+)(?:#[^\[\]|]*)?(?:\|([^\[\]]*))?\]\]")


def log(msg: str) -> None:
    print(msg, flush=True)


def _sin_refs(texto: str) -> str:
    texto = re.sub(r"<ref[^>/]*/>", "", texto)
    texto = re.sub(r"<ref[^>]*>.*?</ref>", "", texto, flags=re.S)
    return re.sub(r"\{\{efn[^{}]*\}\}", "", texto)


def _tabla(texto: str, inicio: str) -> str:
    """Wikitexto de la primera tabla que aparece después de `inicio`."""
    i = texto.index(inicio)
    a = texto.index("{|", i)
    b = texto.index("\n|}", a)
    return texto[a:b]


def _jugador(celda: str) -> tuple[str, str] | None:
    """(título del artículo, nombre visible) de la celda del jugador."""
    m = re.search(r"\{\{sortname\|([^{}]*)\}\}", celda)
    if m:
        partes = m.group(1).split("|")
        posicionales = [p for p in partes if "=" not in p]
        nombre = " ".join(p.strip() for p in posicionales[:2] if p.strip())
        titulo = posicionales[2].strip() if len(posicionales) > 2 and posicionales[2].strip() else nombre
        dab = next((p.split("=", 1)[1].strip() for p in partes if p.startswith("dab=")), None)
        if dab and len(posicionales) <= 2:
            titulo = f"{nombre} ({dab})"
        return titulo, nombre
    m = _ENLACE.search(celda)
    if m:
        return m.group(1).strip(), (m.group(2) or m.group(1)).strip()
    return None


def _texto_enlace(celda: str) -> str:
    m = _ENLACE.search(celda)
    if m:
        return (m.group(2) or m.group(1)).strip()
    return re.sub(r"\{\{[^{}]*\}\}", "", celda).strip()


def _numero(celda: str) -> float | None:
    m = re.search(r"\d+(?:\.\d+)?", re.sub(r"\{\{[^{}]*\}\}", "", celda).replace(",", ""))
    return float(m.group()) if m else None


def _dividir(linea: str) -> list[str]:
    """Separa por '||' o '!!' sin cortar dentro de plantillas {{…}} ni enlaces [[…]]."""
    partes, actual, nivel, i = [], "", 0, 0
    while i < len(linea):
        dos = linea[i:i + 2]
        if dos in ("{{", "[["):
            nivel += 1
        elif dos in ("}}", "]]"):
            nivel = max(0, nivel - 1)
        if nivel == 0 and dos in ("||", "!!"):
            partes.append(actual)
            actual, i = "", i + 2
            continue
        if dos in ("{{", "[[", "}}", "]]"):
            actual, i = actual + dos, i + 2
            continue
        actual, i = actual + linea[i], i + 1
    return partes + [actual]


def _celdas(fila: str) -> list[str]:
    """Celdas de una fila de tabla (admite '|' por línea y '||' en la misma línea)."""
    celdas = []
    for linea in fila.split("\n"):
        linea = linea.strip()
        if not linea or linea[0] not in "|!" or linea.startswith("|+"):
            continue
        for c in _dividir(linea[1:]):
            # Quita atributos de la celda: 'style="..."| valor'
            m = re.match(r'^\s*(?:[a-z-]+\s*=\s*"?[^"|]*"?\s*)+\|(?!\|)(.*)$', c, flags=re.S)
            celdas.append((m.group(1) if m else c).strip())
    return celdas


def _desde_jugador(celdas: list[str]) -> list[str]:
    """Celdas a partir de la del jugador (las filas con puesto empatado no traen el puesto)."""
    for i, c in enumerate(celdas):
        if "flagicon" in c or "sortname" in c:
            return celdas[i:]
    return []


def fichajes(texto: str) -> list[dict]:
    tabla = _sin_refs(_tabla(texto, "==Highest transfer records in association football=="))
    salida = []
    for fila in tabla.split("\n|-")[1:]:
        celdas = _desde_jugador(_celdas(fila))
        # Jugador, desde, hacia, posición, € millones, £ millones, año
        if len(celdas) < 7:
            continue
        jugador = _jugador(celdas[0])
        monto = _numero(celdas[4])
        anio = re.search(r"\b(19|20)\d\d\b", celdas[6])
        if not jugador or not monto or not anio:
            continue
        salida.append({"titulo": jugador[0], "nombre": jugador[1], "origen": _texto_enlace(celdas[1]),
                       "destino": _texto_enlace(celdas[2]), "monto": monto, "anio": int(anio.group())})
    return salida


def asistencias(texto: str) -> list[dict]:
    tabla = _sin_refs(_tabla(texto, "===Assists==="))
    salida = []
    for fila in tabla.split("\n|-")[1:]:
        celdas = _desde_jugador(_celdas(fila))
        # Jugador, asistencias, partidos, …
        if len(celdas) < 3:
            continue
        jugador = _jugador(celdas[0])
        a, p = _numero(celdas[1]), _numero(celdas[2])
        if jugador and a:
            salida.append({"titulo": jugador[0], "nombre": jugador[1], "asistencias": int(a),
                           "partidos": int(p) if p else None})
    return salida


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
    log("\n=== Reporte del paso 9: listas de Wikipedia ===")
    for k, v in resumen.items():
        log(f"  {k}: {v}")


def correr(conn) -> dict:
    arts = {a["titulo_pedido"]: a for a in wp.articulos([ART_FICHAJES, ART_ASISTENCIAS])}
    f = fichajes(arts[ART_FICHAJES]["texto"])
    a = asistencias(arts[ART_ASISTENCIAS]["texto"])
    log(f"{len(f)} fichajes y {len(a)} asistidores leídos")

    qid_de = wp.qids_de_titulos({x["titulo"] for x in f + a})
    existentes = {q for (q,) in conn.execute("select qid from jugadores")}
    def qid(x):
        q = qid_de.get(x["titulo"])
        return q if q in existentes else None

    sin_jugador = sorted({x["nombre"] for x in f + a if not qid(x)})
    with conn.transaction():
        conn.execute("delete from fichajes")
        conn.execute("delete from asistencias")
        filas = {}
        for x in f:
            clave = f"{qid(x) or x['nombre']}|{x['origen']}|{x['destino']}|{x['anio']}"
            filas[clave] = (clave, qid(x), x["nombre"], x["origen"], x["destino"], x["monto"], x["anio"],
                            ART_FICHAJES, arts[ART_FICHAJES]["revision"])
        conn.cursor().executemany(
            """insert into fichajes (id, jugador_qid, jugador_texto, origen, destino, monto_eur, anio, articulo, revision)
               values (%s, %s, %s, %s, %s, %s, %s, %s, %s)""", list(filas.values()))
        conn.cursor().executemany(
            """insert into asistencias (id, jugador_qid, jugador_texto, competicion, asistencias, partidos, articulo, revision)
               values (%s, %s, %s, %s, %s, %s, %s, %s) on conflict (id) do nothing""",
            [(f"Premier League|{qid(x) or x['nombre']}", qid(x), x["nombre"], "Premier League", x["asistencias"],
              x["partidos"], ART_ASISTENCIAS, arts[ART_ASISTENCIAS]["revision"]) for x in a])
    return {"fichajes": len(f), "asistidores": len(a), "sin_jugador_en_la_base": sin_jugador}


if __name__ == "__main__":
    main()
