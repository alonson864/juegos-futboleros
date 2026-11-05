"""Lectura de artículos de Wikipedia (en inglés) de futbolistas.

Extrae, siguiendo enlaces (no interpretando prosa):
  - Ficha ("Infobox football biography"): clubes y selecciones con años, partidos y
    goles, más la fecha "al día" que indica el propio artículo (club-update).
  - Palmarés ("Honours"): cada título con el enlace a la competición y a la edición.

Contenido de Wikipedia con licencia CC BY-SA 4.0: hay que dar crédito al mostrarlo.
"""

from __future__ import annotations

import re
from typing import Iterator

import wikidata as wd

API = "https://en.wikipedia.org/w/api.php"

_ENLACE = re.compile(r"\[\[([^\[\]|#]+)(?:#[^\[\]|]*)?(?:\|([^\[\]]*))?\]\]")
_ANIO = re.compile(r"\b(1[89]\d\d|20\d\d)\b")


# ---------------------------------------------------------------------------
# Descarga
# ---------------------------------------------------------------------------

def articulos(titulos: list[str]) -> Iterator[dict]:
    """Texto, número de revisión y fecha de cada artículo (de a 50 por pedido)."""
    for i in range(0, len(titulos), 50):
        lote = titulos[i : i + 50]
        datos = wd._pedir("GET", API, params={
            "action": "query", "titles": "|".join(lote), "prop": "revisions",
            "rvprop": "content|ids|timestamp", "rvslots": "main", "redirects": 1,
            "format": "json", "formatversion": 2,
        }).json()
        # Los títulos pedidos pueden haber sido normalizados o redirigidos
        origen = {t: t for t in lote}
        for n in datos.get("query", {}).get("normalized", []) + datos.get("query", {}).get("redirects", []):
            origen[n["to"]] = origen.get(n["from"], n["from"])
        for p in datos.get("query", {}).get("pages", []):
            if "revisions" not in p:
                continue
            rev = p["revisions"][0]
            yield {
                "titulo_pedido": origen.get(p["title"], p["title"]),
                "titulo": p["title"],
                "revision": rev["revid"],
                "fecha_revision": rev["timestamp"],
                "texto": rev["slots"]["main"]["content"],
            }


def qids_de_titulos(titulos: set[str]) -> dict[str, str]:
    """Título de artículo -> código de Wikidata (sigue redirecciones)."""
    salida: dict[str, str] = {}
    lista = sorted(titulos)
    for i in range(0, len(lista), 50):
        lote = lista[i : i + 50]
        datos = wd._pedir("GET", API, params={
            "action": "query", "titles": "|".join(lote), "prop": "pageprops",
            "ppprop": "wikibase_item", "redirects": 1, "format": "json", "formatversion": 2,
        }).json()
        q = datos.get("query", {})
        destino = {t: t for t in lote}
        for n in q.get("normalized", []):
            destino[n["from"]] = n["to"]
        redir = {r["from"]: r["to"] for r in q.get("redirects", [])}
        por_titulo = {p["title"]: p.get("pageprops", {}).get("wikibase_item") for p in q.get("pages", [])}
        for t in lote:
            final = destino[t]
            final = redir.get(final, final)
            if por_titulo.get(final):
                salida[t] = por_titulo[final]
    return salida


# ---------------------------------------------------------------------------
# Limpieza de wikitexto
# ---------------------------------------------------------------------------

def _quitar_plantillas(texto: str, nombres: tuple[str, ...]) -> str:
    """Quita plantillas {{nombre ...}} (con anidamiento) cuyos nombres empiezan como `nombres`."""
    salida, i = [], 0
    bajo = texto.lower()
    while i < len(texto):
        if texto.startswith("{{", i) and any(bajo.startswith("{{" + n, i) for n in nombres):
            nivel, j = 0, i
            while j < len(texto):
                if texto.startswith("{{", j):
                    nivel, j = nivel + 1, j + 2
                elif texto.startswith("}}", j):
                    nivel, j = nivel - 1, j + 2
                    if nivel == 0:
                        break
                else:
                    j += 1
            i = j
        else:
            salida.append(texto[i])
            i += 1
    return "".join(salida)


def limpiar(texto: str) -> str:
    texto = re.sub(r"<!--.*?-->", "", texto, flags=re.S)
    texto = re.sub(r"<ref[^>/]*/>", "", texto)
    texto = re.sub(r"<ref[^>]*>.*?</ref>", "", texto, flags=re.S)
    return _quitar_plantillas(texto, ("efn", "refn", "sfn", "cite", "citation", "#tag", "notetag", "r|", "rp",
                                      "for|", "for ", "main|", "see also", "further", "see|"))


def _bloque_plantilla(texto: str, inicio: int) -> str:
    nivel, j = 0, inicio
    while j < len(texto):
        if texto.startswith("{{", j):
            nivel, j = nivel + 1, j + 2
        elif texto.startswith("}}", j):
            nivel, j = nivel - 1, j + 2
            if nivel == 0:
                return texto[inicio:j]
        else:
            j += 1
    return texto[inicio:]


def _parametros(plantilla: str) -> dict[str, str]:
    """Separa los parámetros de una plantilla por '|' de primer nivel."""
    cuerpo = plantilla[2:-2]
    partes, actual, llaves, corchetes, i = [], [], 0, 0, 0
    while i < len(cuerpo):
        dos = cuerpo[i : i + 2]
        if dos == "{{":
            llaves += 1; actual.append(dos); i += 2; continue
        if dos == "}}":
            llaves -= 1; actual.append(dos); i += 2; continue
        if dos == "[[":
            corchetes += 1; actual.append(dos); i += 2; continue
        if dos == "]]":
            corchetes -= 1; actual.append(dos); i += 2; continue
        if cuerpo[i] == "|" and llaves == 0 and corchetes == 0:
            partes.append("".join(actual)); actual = []
        else:
            actual.append(cuerpo[i])
        i += 1
    partes.append("".join(actual))
    params = {}
    for p in partes[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.strip().lower()] = v.strip()
    return params


def _entero(valor: str | None) -> int | None:
    if not valor:
        return None
    valor = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", valor)   # [[Lista de goles|67]] -> 67
    m = re.search(r"\d+", valor.replace(",", ""))
    return int(m.group()) if m else None


def _anios(valor: str) -> tuple[int | None, int | None]:
    anios = [int(a) for a in _ANIO.findall(valor)]
    if not anios:
        return None, None
    abierto = bool(re.search(r"[–-]\s*$", valor.strip()))
    return anios[0], (None if abierto and len(anios) == 1 else anios[-1])


# ---------------------------------------------------------------------------
# Ficha
# ---------------------------------------------------------------------------

def ficha(texto: str) -> dict | None:
    texto = limpiar(texto)
    m = re.search(r"\{\{\s*Infobox football biography", texto, flags=re.I)
    if not m:
        return None
    # La plantilla acepta "national_team1" o "nationalteam1", "club_update" o "club-update"
    p = {k.replace("_", "").replace("-", ""): v for k, v in _parametros(_bloque_plantilla(texto, m.start())).items()}

    def filas(prefijo_anio: str, prefijo_equipo: str, prefijo_pj: str, prefijo_gol: str, seleccion: bool):
        salida = []
        for n in range(1, 60):
            equipo = p.get(f"{prefijo_equipo}{n}")
            if not equipo:
                continue
            enlace = _ENLACE.search(equipo)
            desde, hasta = _anios(p.get(f"{prefijo_anio}{n}", ""))
            salida.append({
                "orden": n,
                "seleccion": seleccion,
                "equipo_titulo": enlace.group(1).strip() if enlace else None,
                "equipo_texto": re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", equipo).replace("→", "").strip(),
                "prestamo": "loan" in equipo.lower(),
                "desde": desde,
                "hasta": hasta,
                "partidos": _entero(p.get(f"{prefijo_pj}{n}")),
                "goles": _entero(p.get(f"{prefijo_gol}{n}")),
            })
        return salida

    return {
        "clubes": filas("years", "clubs", "caps", "goals", False),
        "selecciones": filas("nationalyears", "nationalteam", "nationalcaps", "nationalgoals", True),
        "al_dia_clubes": _texto_fecha(p.get("clubupdate")),
        "al_dia_seleccion": _texto_fecha(p.get("nationalteamupdate")),
    }


def _texto_fecha(valor: str | None) -> str | None:
    if not valor:
        return None
    # {{date|2026-10-30}}, {{dts|...}} o texto plano: se guarda legible
    valor = re.sub(r"\{\{[^|}]*\|", "", valor).replace("}}", "").replace("|", " ")
    return re.sub(r"\s+", " ", valor).strip() or None


# ---------------------------------------------------------------------------
# Palmarés
# ---------------------------------------------------------------------------

# Puestos que NO son títulos: subcampeón, 2.º/3.º, plata/bronce, nominado, finalista…
_NO_TITULO = re.compile(
    r"runner[s -]?up|(second|third|fourth)[ -]place|\b(2nd|3rd|4th)\b|finalist|semi-?final|"
    r"silver|bronze|nomin|shortlist|candidate|podium|top three|"
    r"\b(?:[2-9]|[1-9]\d)(?:st|nd|rd|th)\b|\bplace\b|\branked\b|"      # puestos: (6th place), (8th), (26th)
    r"\b(fifth|sixth|seventh|eighth|ninth|tenth)\b", re.I)
_TEMPORADA = re.compile(r"\b(1[89]\d\d|20\d\d)\s*[–/-]\s*(\d{2,4})\b|\b(1[89]\d\d|20\d\d)\b")


def _partes(segmento: str) -> list[str]:
    """Separa por comas de primer nivel (fuera de [[...]] y paréntesis)."""
    partes, actual, nivel = [], [], 0
    for i, ch in enumerate(segmento):
        if segmento.startswith("[[", i) or ch == "(":
            nivel += 1
        elif segmento.startswith("]]", i) or ch == ")":
            nivel -= 1
        if ch == "," and nivel <= 0:
            partes.append("".join(actual)); actual = []
        else:
            actual.append(ch)
    partes.append("".join(actual))
    return partes


def palmares(texto: str) -> list[dict]:
    """Títulos del palmarés: [{grupo, competicion_titulo, ediciones: [(titulo, etiqueta)], anios}]."""
    texto = limpiar(texto)
    m = re.search(r"^==\s*(Honours|Honors|Titles)\s*==\s*$", texto, flags=re.M | re.I)
    if not m:
        return []
    fin = re.search(r"^==[^=].*==\s*$", texto[m.end():], flags=re.M)
    seccion = texto[m.end(): m.end() + fin.start()] if fin else texto[m.end():]

    titulos, grupo = [], None
    for linea in seccion.split("\n"):
        linea = linea.strip()
        if not linea:
            continue
        # Encabezados de grupo: '''Barcelona''', ;Barcelona, ===Club===
        cab = re.match(r"^(?:'''(.+?)'''|;\s*(.+)|=+\s*(.+?)\s*=+)$", linea)
        if cab:
            grupo = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", next(g for g in cab.groups() if g)).strip("' ")
            continue
        if not linea.startswith("*") or ":" not in linea:
            continue
        cuerpo = linea.lstrip("*").strip()
        antes, despues = cuerpo.split(":", 1)
        if _NO_TITULO.search(antes):
            continue                          # subcampeonatos, terceros puestos, etc.
        comp = _ENLACE.search(antes)
        if not comp:
            continue
        # "2018; runner-up: 2022" o "1958 (third place), 1960": se descarta cada parte que no sea título
        partes = []
        for seg in despues.split(";"):
            # Lo que va antes del primer año/enlace es una etiqueta que aplica a todo el tramo
            prefijo = re.split(r"\[\[|\d", seg, maxsplit=1)[0]
            if _NO_TITULO.search(prefijo):
                continue
            partes += [p for p in _partes(seg) if not _NO_TITULO.search(p)]
        despues = ", ".join(partes)
        ediciones = [(e.group(1).strip(), (e.group(2) or e.group(1)).strip()) for e in _ENLACE.finditer(despues)]
        # Años sin enlace: se guardan como temporada ("2006–07") para no confundir el año
        sin_enlaces = _ENLACE.sub("", despues)
        anios = [m.group(0).replace(" ", "") for m in _TEMPORADA.finditer(sin_enlaces)]
        if not ediciones and not anios:
            continue
        titulos.append({
            "grupo": grupo,
            "competicion_titulo": comp.group(1).strip(),
            "competicion_etiqueta": (comp.group(2) or comp.group(1)).strip(),
            "individual": bool(grupo and re.search(r"individual", grupo, re.I)),
            "ediciones": ediciones,
            "anios": anios,
            "texto": re.sub(r"\s+", " ", re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", cuerpo))[:300],
        })
    return titulos
