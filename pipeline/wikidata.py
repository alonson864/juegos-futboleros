"""Cliente mínimo para Wikidata: consultas SPARQL y lectura de entidades.

Respeta los límites de Wikidata: se identifica, espera entre pedidos y
reintenta con pausas cuando el servicio pide bajar el ritmo.
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path
from typing import Iterable, Iterator

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Wikimedia pide que los programas se identifiquen con un contacto (va en .env).
_contacto = "; ".join(
    v for v in (os.environ.get("WIKIMEDIA_CONTACTO_URL"), os.environ.get("WIKIMEDIA_CONTACTO_EMAIL")) if v
)
AGENTE = f"JuegosFutboleros/0.1 ({_contacto or 'sin contacto'}) python-requests/{requests.__version__}"
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
                # Sin "maxlag": ese parámetro es para programas que editan Wikidata;
                # nosotros solo leemos.
            },
        )
        datos = r.json()
        if "error" in datos:
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


def enlaces_wikipedia(titulo: str, idioma: str = "es") -> list[str]:
    """Códigos Q de los artículos a los que enlaza un artículo de Wikipedia."""
    url = f"https://{idioma}.wikipedia.org/w/api.php"
    params = {
        "action": "query", "titles": titulo, "generator": "links", "gplnamespace": 0,
        "gpllimit": "max", "prop": "pageprops", "ppprop": "wikibase_item",
        "format": "json", "formatversion": 2,
    }
    qids: list[str] = []
    while True:
        datos = _pedir("GET", url, params=params).json()
        for pagina in datos.get("query", {}).get("pages", []):
            q = pagina.get("pageprops", {}).get("wikibase_item")
            if q:
                qids.append(q)
        if "continue" not in datos:
            return qids
        params.update(datos["continue"])


def nombre_futbolistico(etiqueta: str | None, titulo_enwiki: str | None) -> str | None:
    """Prefiere el nombre futbolístico cuando la etiqueta es el nombre legal completo.

    Ej.: etiqueta "Fernando Luiz Rosa" + artículo "Fernandinho" -> "Fernandinho";
         "Leonardo Nascimento de Araujo" + "Leonardo (footballer, born 1969)" -> "Leonardo".
    """
    if not titulo_enwiki:
        return etiqueta
    corto = re.sub(r"\s*\(.*\)\s*$", "", titulo_enwiki).strip()
    if not etiqueta:
        return corto
    pal_corto, pal_etiqueta = corto.lower().split(), etiqueta.lower().split()
    # Apodo de una sola palabra frente a un nombre legal largo (Fernandinho, Leonardo)
    if len(pal_corto) == 1 and len(pal_etiqueta) >= 3:
        return corto
    # Versión corta contenida en el nombre largo (Cristiano Ronaldo dos Santos Aveiro)
    if len(pal_corto) < len(pal_etiqueta) and len(pal_etiqueta) >= 3 and set(pal_corto) <= set(pal_etiqueta):
        return corto
    return etiqueta
