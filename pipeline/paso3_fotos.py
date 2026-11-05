"""Paso 3: autor y licencia de las fotos de los jugadores, desde Wikimedia Commons.

- El paso 2 anota el archivo de foto de cada jugador (propiedad P18 de Wikidata).
- Este paso consulta en Commons la URL, una miniatura, el autor y la licencia.
- Solo se marcan como usables (licencia_libre) las licencias CC0, dominio público,
  CC BY y CC BY-SA. Las demás (por ejemplo "NC" = no comercial) quedan descartadas
  y el sitio muestra el avatar genérico.
- Por defecto solo revisa fotos nuevas o que cambiaron (sin URL todavía).

Uso: pipeline/.venv/bin/python pipeline/paso3_fotos.py [--todas]
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import time

import wikidata as wd
from db import conectar, iniciar_ejecucion, terminar_ejecucion

PASO = "paso3_fotos"
API = "https://commons.wikimedia.org/w/api.php"
ANCHO_MINIATURA = 400

_LIBRE = re.compile(r"^(cc0|public domain|pd\b|pd-|cc[ -]by(-sa)?( \d(\.\d)?)?( [a-z-]+)?$)", re.I)
_NO_LIBRE = re.compile(r"\bnc\b|\bnd\b|non-?commercial|no derivatives|fair use", re.I)


def texto_plano(valor: str | None) -> str | None:
    if not valor:
        return None
    sin_html = re.sub(r"<[^>]+>", "", valor)
    limpio = re.sub(r"\s+", " ", html.unescape(sin_html)).strip()
    return limpio[:300] or None


def es_libre(licencia: str | None) -> bool:
    return bool(licencia and _LIBRE.search(licencia.strip()) and not _NO_LIBRE.search(licencia))


def consultar(archivos: list[str]) -> dict[str, dict]:
    """archivo -> datos de Commons (de a 50 por pedido)."""
    salida: dict[str, dict] = {}
    for i in range(0, len(archivos), 50):
        lote = archivos[i : i + 50]
        titulos = ["File:" + a for a in lote]
        datos = wd._pedir("GET", API, params={
            "action": "query", "titles": "|".join(titulos), "prop": "imageinfo",
            "iiprop": "url|extmetadata", "iiurlwidth": ANCHO_MINIATURA,
            "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl|UsageTerms|Restrictions",
            "iiextmetadatalanguage": "es", "format": "json", "formatversion": 2,
        }).json()
        q = datos.get("query", {})
        destino = {t: t for t in titulos}
        for n in q.get("normalized", []):
            destino[n["from"]] = n["to"]
        por_titulo = {p["title"]: p for p in q.get("pages", [])}
        for a, t in zip(lote, titulos):
            p = por_titulo.get(destino[t])
            if not p or p.get("missing") or not p.get("imageinfo"):
                salida[a] = {"encontrada": False}
                continue
            info = p["imageinfo"][0]
            meta = info.get("extmetadata", {})
            licencia = texto_plano(meta.get("LicenseShortName", {}).get("value"))
            salida[a] = {
                "encontrada": True,
                "url": info.get("url"),
                "miniatura": info.get("thumburl"),
                "autor": texto_plano(meta.get("Artist", {}).get("value")),
                "licencia": licencia,
                "licencia_url": texto_plano(meta.get("LicenseUrl", {}).get("value")),
                "libre": es_libre(licencia),
            }
        if (i // 50) % 20 == 0:
            print(f"  {min(i + 50, len(archivos))}/{len(archivos)} fotos consultadas", flush=True)
    return salida


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--todas", action="store_true", help="revisar todas las fotos, no solo las nuevas")
    args = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)
    inicio = time.time()

    with conectar() as conn:
        ejecucion = iniciar_ejecucion(conn, PASO)
        filtro = "" if args.todas else "where url is null"
        pendientes = [r[0] for r in conn.execute(f"select distinct archivo from imagenes {filtro}")]
        conn.commit()
    print(f"Consultando {len(pendientes)} fotos en Wikimedia Commons…")

    try:
        datos = consultar(pendientes)
        with conectar() as conn:
            with conn.transaction():
                conn.cursor().executemany(
                    """update imagenes set url = %s, url_miniatura = %s, autor = %s, licencia = %s,
                         licencia_url = %s, licencia_libre = %s, actualizado_en = now()
                       where archivo = %s""",
                    [(d.get("url"), d.get("miniatura"), d.get("autor"),
                      d.get("licencia") if d["encontrada"] else "archivo no encontrado en Commons",
                      d.get("licencia_url"), d.get("libre", False), a) for a, d in datos.items()],
                )
            total, libres = conn.execute(
                "select count(*), count(*) filter (where licencia_libre) from imagenes").fetchone()
            sin_foto = conn.execute(
                "select count(*) from jugadores j where not exists "
                "(select 1 from imagenes i where i.jugador_qid = j.qid and i.licencia_libre)").fetchone()[0]
            no_libres = conn.execute(
                "select coalesce(licencia, '(sin datos)'), count(*) from imagenes where not licencia_libre "
                "group by 1 order by 2 desc limit 8").fetchall()
            conn.commit()
    except Exception as e:
        with conectar() as conn:
            terminar_ejecucion(conn, ejecucion, "error", {"error": str(e)[:500]})
        raise

    resumen = {"consultadas": len(datos), "fotos": total, "libres": libres,
               "jugadores_sin_foto_usable": sin_foto, "no_libres": dict(no_libres),
               "minutos": round((time.time() - inicio) / 60, 1)}
    with conectar() as conn:
        terminar_ejecucion(conn, ejecucion, "ok", resumen)

    print("\n=== Reporte del paso 3: fotos ===")
    print(f"Fotos consultadas ahora: {len(datos)}")
    print(f"Fotos en la base: {total} | con licencia libre (usables): {libres}")
    print(f"Jugadores sin foto usable (se mostrará avatar genérico): {sin_foto}")
    print("Licencias descartadas más comunes:")
    for lic, n in no_libres:
        print(f"  {lic:<40} {n}")


if __name__ == "__main__":
    main()
