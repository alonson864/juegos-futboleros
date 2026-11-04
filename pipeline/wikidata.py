"""Cliente mínimo para Wikidata: consultas SPARQL y lectura de entidades.

Respeta los límites de Wikidata: se identifica, espera entre pedidos y
reintenta con pausas cuando el servicio pide bajar el ritmo.
"""

from __future__ import annotations

import sys
import time
from typing import Iterable, Iterator

import requests

AGENTE = "JuegosFutboleros/0.1 (pipeline de datos personal; python-requests)"
SPARQL_URL = "https://query.wikidata.org/sparql"
API_URL = "https://www.wikidata.org/w/api.php"
PAUSA_ENTRE_PEDIDOS = 1.0  # segundos

_sesion = requests.Session()
_sesion.headers["User-Agent"] = AGENTE


def _pedir(metodo: str, url: str, **kwargs) -> requests.Response:
    for intento in range(8):
        try:
            r = _sesion.request(metodo, url, timeout=120, **kwargs)
        except requests.RequestException as e:
            espera = 15 * (intento + 1)
            print(f"  (error de red: {type(e).__name__}; reintento en {espera}s)", file=sys.stderr)
            time.sleep(espera)
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            espera = int(r.headers.get("Retry-After") or 0) or 30 * (intento + 1)
            print(f"  (Wikidata pidió esperar: HTTP {r.status_code}; espero {espera}s)", file=sys.stderr)
            time.sleep(espera)
            continue
        r.raise_for_status()
        time.sleep(PAUSA_ENTRE_PEDIDOS)
        return r
    raise RuntimeError(f"Wikidata no respondió después de varios intentos: {url}")


def sparql(consulta: str) -> list[dict]:
    """Corre una consulta SPARQL y devuelve las filas como dict {variable: valor}."""
    r = _pedir(
        "POST",
        SPARQL_URL,
        data={"query": consulta},
        headers={"Accept": "application/sparql-results+json"},
    )
    filas = []
    for b in r.json()["results"]["bindings"]:
        filas.append({k: v["value"] for k, v in b.items()})
    return filas


def qid(uri: str) -> str:
    """'http://www.wikidata.org/entity/Q123' -> 'Q123'"""
    return uri.rsplit("/", 1)[-1]


def entidades(qids: Iterable[str], props: str = "labels|claims|sitelinks",
              idiomas: str = "es|en|pt|it|fr|de") -> Iterator[dict]:
    """Lee entidades de a 50 (el máximo que permite la API)."""
    lista = sorted(set(qids))
    for i in range(0, len(lista), 50):
        lote = lista[i : i + 50]
        r = _pedir(
            "GET",
            API_URL,
            params={
                "action": "wbgetentities",
                "ids": "|".join(lote),
                "props": props,
                "languages": idiomas,
                "format": "json",
                "maxlag": 5,
            },
        )
        datos = r.json()
        if "error" in datos:
            # maxlag: el servidor está cargado; esperamos y repetimos el mismo lote
            if datos["error"].get("code") == "maxlag":
                time.sleep(10)
                yield from entidades(lote, props, idiomas)
                continue
            raise RuntimeError(f"Error de la API de Wikidata: {datos['error']}")
        for e in datos.get("entities", {}).values():
            if "missing" not in e:
                yield e


def etiqueta(entidad: dict, preferidos: tuple[str, ...] = ("es", "en")) -> str | None:
    labels = entidad.get("labels", {})
    for idioma in preferidos:
        if idioma in labels:
            return labels[idioma]["value"]
    for valor in labels.values():
        return valor["value"]
    return None


def valores(entidad: dict, propiedad: str) -> list[str]:
    """Códigos Q de una propiedad (ignora valores 'desconocido' y los marcados como obsoletos)."""
    salida = []
    for st in entidad.get("claims", {}).get(propiedad, []):
        if st.get("rank") == "deprecated":
            continue
        dv = st.get("mainsnak", {}).get("datavalue", {})
        if dv.get("type") == "wikibase-entityid":
            salida.append(dv["value"]["id"])
    return salida


# Sitios que terminan en "wiki" pero no son Wikipedias
_NO_WIKIPEDIA = {
    "commonswiki", "specieswiki", "metawiki", "mediawikiwiki", "wikidatawiki", "sourceswiki",
    "wikimaniawiki", "outreachwiki", "foundationwiki", "incubatorwiki", "wikifunctionswiki",
    "testwiki", "test2wiki", "testwikidatawiki", "officewiki", "strategywiki", "donatewiki",
}


def contar_wikipedias(entidad: dict) -> int:
    """Cuántas Wikipedias tienen artículo (no cuenta Wikiquote, Commons, etc.)."""
    return sum(
        1
        for sitio in entidad.get("sitelinks", {})
        if sitio.endswith("wiki") and sitio not in _NO_WIKIPEDIA
    )


def fecha(valor: str | None) -> str | None:
    """'1929-09-01T00:00:00Z' -> '1929-09-01'. Ignora años antes de Cristo o vacíos."""
    if not valor or valor.startswith("-"):
        return None
    return valor[:10]
