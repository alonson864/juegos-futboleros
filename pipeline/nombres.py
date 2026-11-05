"""Ayudas de texto para mostrar nombres de forma más corta y para buscar sin tildes."""

from __future__ import annotations

import re
import unicodedata

# Partes "legales" del nombre de un club que no hacen falta para reconocerlo
_SOBRANTES = [
    r"\bAssociation Football Club\b", r"\bFootball Club\b", r"\bClub de Fútbol\b", r"\bFútbol Club\b",
    r"\bFutebol Clube\b", r"\bFutbol Club\b", r"\bSociedad Anónima Deportiva\b", r"\bS\.A\.D\.\b",
    r"^Club Atlético\s+", r"^Club Deportivo\s+", r"^Club\s+",
    r"^Società Sportiva Calcio\s+", r"^Società Sportiva\s+", r"^Unione Calcio\s+", r"^Associazione Calcio\s+",
    r"\s+Calcio(\s+\d{4})?$", r"\s+\d{4}$",
    r"\s+A\.\s?F\.\s?C\.$", r"\s+F\.\s?C\.$", r"^F\.\s?C\.\s+", r"^A\.\s?C\.\s+(?=\w{4,})",
]


def club_corto(nombre: str) -> str:
    corto = nombre
    for patron in _SOBRANTES:
        corto = re.sub(patron, "", corto)
    corto = re.sub(r"\s{2,}", " ", corto).strip(" -,&")
    corto = re.sub(r"\s+(Cricket|and|y)$", "", corto)        # "Genoa Cricket & Football Club" -> "Genoa"
    return corto if len(corto) >= 3 else nombre


def normalizar(texto: str) -> str:
    """minúsculas, sin tildes ni signos: 'Ronaldo Nazário' -> 'ronaldo nazario'."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", sin_tildes.lower()).strip()


# Solo selecciones mayores masculinas de fútbol ("selección de fútbol de Perú"),
# no B, femeninas, de playa, militares, juveniles ni de otros deportes.
_SELECCION_MAYOR = re.compile(r"^selecci[oó]n (de fútbol |nacional de fútbol )?(de la |del |de )", re.I)
_NO_MAYOR = re.compile(r"\bB\b|\bA2\b|femenin|playa|militar|ol[ií]mpic|sub-?\d|juvenil|amateur|"
                       r"universitari|reserva|críquet|baloncesto|rugby|hockey|sala|futsal", re.I)


def nombre_seleccion(nombre: str, pais: str | None = None) -> str | None:
    """'selección de fútbol del Perú' -> 'Perú'; None si no es una selección mayor de fútbol.

    Si el nombre tiene otra forma ("Selección Chilena de Fútbol"), se usa el país.
    """
    if _NO_MAYOR.search(nombre) or "fútbol" not in nombre.lower():
        return None
    if _SELECCION_MAYOR.match(nombre):
        p = _SELECCION_MAYOR.sub("", nombre).strip()
        return p[:1].upper() + p[1:] if p else None
    return pais if nombre.lower().startswith("selección") else None
