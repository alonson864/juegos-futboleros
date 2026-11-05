"""Preguntas de Dato Falso sobre títulos y premios (lee SOLO de la base).

Tipos:
  ganadores_de_titulo: "Todos estos ganaron [la Champions / el Balón de Oro…]"  (4 sí + 1 no)
  equipos_campeones:   "Todos estos clubes/selecciones ganaron [torneo]"        (4 sí + 1 no)
  titulos_de_jugador:  "[Jugador] ganó todos estos títulos"                     (4 reales + 1 falso)

Seguridad:
  - Un jugador solo puede ser la opción falsa si leímos su palmarés en Wikipedia
    (tabla jugadores_wikipedia). Que no figure un título no prueba nada si nunca
    leímos su palmarés.
  - La opción falsa no puede aparecer en NINGÚN registro: títulos originales, títulos
    con correcciones, valores de la tabla de correcciones, premios de Wikidata (paso 5)
    y, para equipos, campeones originales/corregidos y fichas equivalentes (alias).
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field

from nombres import club_corto, nombre_seleccion

# Familias de competiciones: artículos de Wikipedia en inglés que cuentan como lo mismo
FAMILIAS = {
    "champions": ["UEFA Champions League", "European Cup"],
    "mundial": ["FIFA World Cup"],
    "eurocopa": ["UEFA European Championship"],
    "copa_america": ["Copa América"],
    "balon_de_oro": ["Ballon d'Or", "FIFA Ballon d'Or"],
    "bota_de_oro": ["European Golden Shoe"],
    "puskas": ["FIFA Puskás Award"],
}
# "Jugador Mundial de la FIFA" / "FIFA Balón de Oro" / "The Best" quedan fuera por ahora: en
# Wikipedia a veces vienen en una sola línea mezclados según la época y no se separan bien.
# Cómo se nombra cada familia en las preguntas: (con artículo, corto)
TEXTO = {
    "champions": ("la Champions League", "Champions League"),
    "mundial": ("el Mundial", "Mundial"),
    "eurocopa": ("la Eurocopa", "Eurocopa"),
    "copa_america": ("la Copa América", "Copa América"),
    "balon_de_oro": ("el Balón de Oro", "Balón de Oro"),
    "bota_de_oro": ("la Bota de Oro", "Bota de Oro"),
    "puskas": ("el Premio Puskás", "Premio Puskás"),
}
FAMA_MINIMA_EQUIPO = 300_000  # suma de visitas de sus jugadores (para que la opción falsa sea conocida)
TORNEOS_CLUBES = {"champions"}
TORNEOS_SELECCIONES = {"mundial", "eurocopa", "copa_america"}
PREMIOS = {"balon_de_oro", "bota_de_oro", "puskas"}


@dataclass
class Datos:
    familia_de: dict[str, str]                       # qid de competición -> familia
    nombre_familia: dict[str, str]                   # familia -> nombre en español (de Wikidata)
    jugadores: dict[str, tuple[str, int, set[str]]]  # qid -> (nombre, visitas, nacionalidades)
    leidos: set[str]                                 # jugadores con palmarés leído en Wikipedia
    titulos: dict[str, set[tuple[str, int]]]         # jugador -> {(familia, año)} (con correcciones)
    registros: dict[str, set[tuple[str, int | None]]] = field(default_factory=dict)  # TODO registro
    campeones: dict[str, dict[str, list[int]]] = field(default_factory=dict)  # familia -> equipo -> años
    campeones_registros: dict[str, set[str]] = field(default_factory=dict)    # familia -> TODO equipo
    nombre_equipo: dict[str, str] = field(default_factory=dict)
    equipos_de: dict[str, set[str]] = field(default_factory=dict)    # jugador -> clubes y selecciones
    anios_activo: dict[str, tuple[int, int]] = field(default_factory=dict)
    alias: dict[str, set[str]] = field(default_factory=dict)
    tipo_equipo: dict[str, str] = field(default_factory=dict)        # club, seleccion, juvenil…
    continente_equipo: dict[str, str | None] = field(default_factory=dict)


def cargar(conn) -> Datos:
    familia_de: dict[str, str] = {}
    nombre_familia: dict[str, str] = {}
    for qid, nombre, articulo in conn.execute("select qid, nombre, articulo_en from competiciones"):
        for fam, articulos in FAMILIAS.items():
            if articulo in articulos:
                familia_de[qid] = fam
                if articulo == articulos[0] or fam not in nombre_familia:
                    nombre_familia[fam] = nombre

    jugadores = {q: (n, p, set(nac or [])) for q, n, p, nac in conn.execute(
        "select qid, nombre, coalesce(visitas, 0), nacionalidades from jugadores_final where nombre !~ '^Q[0-9]+$'")}
    leidos = {r[0] for r in conn.execute("select jugador_qid from jugadores_wikipedia")}

    def fila_a_titulo(comp, anio, individual):
        fam = familia_de.get(comp)
        if not fam:
            return None
        if fam not in PREMIOS and individual:     # "Individual: FIFA World Cup" no es el título
            return None
        return fam, anio

    titulos: dict[str, set] = defaultdict(set)
    for j, comp, anio, ind in conn.execute(
            "select jugador_qid, competicion_qid, anio, individual from titulos_jugador_final"):
        t = fila_a_titulo(comp, anio, ind)
        if t and t[1]:
            titulos[j].add(t)

    # Premios con un solo ganador por año: si aparecen varios ganadores el mismo año, ese
    # dato es dudoso y no se usa como verdadero (sí cuenta como "registro" para la seguridad).
    ganadores_por_anio: dict[tuple[str, int], set[str]] = defaultdict(set)
    for j, ts in titulos.items():
        for fam, a in ts:
            ganadores_por_anio[(fam, a)].add(j)
    maximo = {"balon_de_oro": 1, "puskas": 1, "bota_de_oro": 2}
    dudosos = {k for k, js in ganadores_por_anio.items() if len(js) > maximo.get(k[0], 10_000)}
    for j in titulos:
        titulos[j] = {t for t in titulos[j] if t not in dudosos}

    # Todos los registros (originales + corregidos + valores de correcciones), para la seguridad
    registros: dict[str, set] = defaultdict(set)
    for j, comp, anio, ind in conn.execute(
            "select jugador_qid, competicion_qid, anio, individual from titulos_jugador "
            "union all select jugador_qid, competicion_qid, anio, individual from titulos_jugador_final"):
        fam = familia_de.get(comp)
        if fam:
            registros[j].add((fam, anio))                       # incluye "Individual" por las dudas
    for j, campo, valor, comp, anio in conn.execute(
            """select t.jugador_qid, c.campo, c.valor, t.competicion_qid, t.anio from correcciones c
               join titulos_jugador t on t.id = c.registro where c.tabla = 'titulos_jugador'"""):
        if campo == "competicion_qid" and isinstance(valor, str) and valor in familia_de:
            registros[j].add((familia_de[valor], anio))
        if campo == "anio" and isinstance(valor, int) and comp in familia_de:
            registros[j].add((familia_de[comp], valor))

    alias: dict[str, set[str]] = defaultdict(set)
    for a, c in conn.execute("select qid, club_qid from clubes_alias"):
        alias[a].add(c)
        alias[c].add(a)

    campeones: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for comp, campeon, anio in conn.execute(
            "select competicion_qid, campeon_qid, anio from ediciones_final where campeon_qid is not null"):
        fam = familia_de.get(comp)
        if fam and anio:
            campeones[fam][campeon].append(anio)
    campeones_registros: dict[str, set[str]] = defaultdict(set)
    for comp, campeon in conn.execute(
            "select competicion_qid, campeon_qid from ediciones union select competicion_qid, campeon_qid "
            "from ediciones_final"):
        fam = familia_de.get(comp)
        if fam and campeon:
            campeones_registros[fam] |= {campeon} | alias[campeon]
    for comp, valor in conn.execute(
            """select e.competicion_qid, c.valor from correcciones c join ediciones e on e.qid = c.registro
               where c.tabla = 'ediciones' and c.campo = 'campeon_qid'"""):
        fam = familia_de.get(comp)
        if fam and isinstance(valor, str):
            campeones_registros[fam] |= {valor} | alias[valor]

    nombre_equipo, tipo_equipo, continente_equipo = {}, {}, {}
    paises, continentes = {}, {}
    for q, n, cont in conn.execute("select qid, nombre, continente from paises"):
        paises[q], continentes[q] = n, cont
    for q, n, t, pais in conn.execute("select qid, nombre, tipo, pais_qid from clubes_final"):
        # Las selecciones mayores se muestran con el nombre del país ("Bolivia")
        # Selecciones con su nombre real ("Inglaterra", no "Reino Unido"); clubes con nombre corto
        if t == "seleccion":
            sel = nombre_seleccion(n, paises.get(pais))
            nombre_equipo[q] = sel or n
            if not sel:
                t = "otro"            # femeninas, B, de otros deportes: nunca se usan como opción
        else:
            nombre_equipo[q] = club_corto(n)
        continente_equipo[q] = continentes.get(pais)
        tipo_equipo[q] = t
    for q, n in conn.execute("select campeon_qid, campeon_nombre from ediciones where campeon_qid is not null"):
        nombre_equipo.setdefault(q, n)

    equipos_de: dict[str, set[str]] = defaultdict(set)
    anios: dict[str, list[int]] = defaultdict(list)
    for j, club, ini, fin in conn.execute("select jugador_qid, club_qid, inicio, fin from pasos_por_club_final"):
        equipos_de[j] |= {club} | alias[club]
        anios[j] += [x.year for x in (ini, fin) if x]
    for j, eq, desde, hasta in conn.execute("select jugador_qid, equipo_qid, desde, hasta from carrera_wikipedia"):
        if eq:
            equipos_de[j] |= {eq} | alias[eq]
        anios[j] += [x for x in (desde, hasta) if x]
    conn.commit()
    nombre_familia = {f: TEXTO[f][1] for f in nombre_familia if f in TEXTO}
    return Datos(familia_de, nombre_familia, jugadores, leidos, titulos, registros, campeones,
                 campeones_registros, nombre_equipo, equipos_de,
                 {j: (min(a), max(a)) for j, a in anios.items() if a}, alias, tipo_equipo, continente_equipo)


# ---------------------------------------------------------------------------

def tramo(d: Datos, dif: str) -> set[str]:
    """Jugadores leídos según dificultad: tercio más famoso, medio o menos famoso."""
    orden = sorted(d.leidos & d.jugadores.keys(), key=lambda q: -d.jugadores[q][1])
    n = len(orden) // 3 or 1
    return set({"facil": orden[:n], "intermedio": orden[n:2 * n], "dificil": orden[2 * n:]}[dif])


def texto_edicion(fam: str, anio: int) -> str:
    return f"{anio - 1}–{anio % 100:02d}" if fam in TORNEOS_CLUBES or fam == "bota_de_oro" else str(anio)


def pronombre(fam: str) -> str:
    return "la" if TEXTO[fam][0].startswith("la ") else "lo"


def lista(nombres: list[str]) -> str:
    return nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " y " + nombres[-1]


def gano(d: Datos, j: str, fam: str) -> bool:
    return any(f == fam for f, _ in d.titulos.get(j, ()))


def algun_registro(d: Datos, j: str, fam: str, anio: int | None = None) -> bool:
    return any(f == fam and (anio is None or a is None or a == anio) for f, a in d.registros.get(j, ()))


# ---------------------------------------------------------------------------
# Validación (al crear y al revalidar)
# ---------------------------------------------------------------------------

def es_valida(p: dict, d: Datos) -> bool:
    ops = p["opciones"]
    falsas = [o for o in ops if not o["verdadera"]]
    verdaderas = [o for o in ops if o["verdadera"]]
    if len(ops) != 5 or len(falsas) != 1:
        return False
    f = falsas[0]["qid"]
    if p["tipo"] == "ganadores_de_titulo":
        fam = p["protagonista"]["qid"]
        return (f in d.leidos and not algun_registro(d, f, fam)
                and all(gano(d, o["qid"], fam) for o in verdaderas))
    if p["tipo"] == "equipos_campeones":
        fam = p["protagonista"]["qid"]
        return (f not in d.campeones_registros.get(fam, set())
                and all(o["qid"] in d.campeones.get(fam, {}) for o in verdaderas))
    if p["tipo"] == "titulos_de_jugador":
        j = p["protagonista"]["qid"]
        ffam, fanio = f.split(":")
        return (j in d.leidos and not algun_registro(d, j, ffam, int(fanio))
                and all(tuple(o["qid"].split(":")) in {(a, str(b)) for a, b in d.titulos.get(j, ())}
                        for o in verdaderas))
    return False


# ---------------------------------------------------------------------------
# Generadores
# ---------------------------------------------------------------------------

def gen_ganadores_de_titulo(d: Datos, dif: str, rng: random.Random, n: int):
    del_tramo = tramo(d, dif)
    familias = list(FAMILIAS)
    rng.shuffle(familias)
    hechas = 0
    for _ in range(n * 3):
        fam = familias[hechas % len(familias)] if familias else None
        if not fam or fam not in d.nombre_familia:
            break
        hechas += 1
        ganadores = [j for j in d.titulos if gano(d, j, fam) and j in d.jugadores]
        # En fácil, ganadores muy conocidos; en las otras, se mezclan con los del tramo
        pool = [j for j in ganadores if j in del_tramo] or (ganadores if dif != "facil" else [])
        if len(pool) < 4:
            continue
        verdaderos = rng.sample(pool, 4)
        equipos_campeones = set(d.campeones.get(fam, {}))
        nacs = set().union(*(d.jugadores[v][2] for v in verdaderos))
        companeros = set().union(*(d.equipos_de.get(v, set()) for v in verdaderos))

        def credibilidad(f: str) -> float:
            s = 0.0
            if d.equipos_de.get(f, set()) & equipos_campeones:
                s += 0.45                      # jugó en un club/selección que sí lo ganó
            if d.equipos_de.get(f, set()) & companeros:
                s += 0.3                       # compartió equipo con alguno de los verdaderos
            if d.jugadores[f][2] & nacs:
                s += 0.15                      # misma nacionalidad
            if any(fm in PREMIOS for fm, _ in d.titulos.get(f, ())) and fam in PREMIOS:
                s += 0.1                       # ganó otro premio individual importante
            return min(s, 1.0)

        candidatos = [f for f in del_tramo if f not in verdaderos and not algun_registro(d, f, fam)]
        puntuados = sorted(((credibilidad(f), f) for f in candidatos), reverse=True)
        minimo, maximo = {"facil": (0.0, 0.6), "intermedio": (0.3, 1.0), "dificil": (0.6, 1.0)}[dif]
        puntuados = [(s, f) for s, f in puntuados if minimo <= s <= maximo]
        if not puntuados:
            continue
        _, falso = rng.choice(puntuados[:5])
        nombre = d.nombre_familia[fam]
        anios = {v: sorted(a for fm, a in d.titulos[v] if fm == fam) for v in verdaderos}
        opciones = [{"texto": d.jugadores[v][0], "qid": v, "verdadera": True} for v in verdaderos]
        opciones.append({"texto": d.jugadores[falso][0], "qid": falso, "verdadera": False})
        rng.shuffle(opciones)
        yield {
            "clave": f"ganadores_de_titulo:{fam}:{falso}:{','.join(sorted(verdaderos))}",
            "tipo": "ganadores_de_titulo",
            "dificultad": dif,
            "afirmacion": f"Todos estos ganaron {TEXTO[fam][0]}",
            "protagonista": {"tipo": "titulo", "qid": fam, "nombre": nombre},
            "opciones": opciones,
            "explicacion": lista([f"{d.jugadores[v][0]} ({', '.join(texto_edicion(fam, a) for a in anios[v])})"
                                  for v in verdaderos])
                           + f" ganaron {TEXTO[fam][0]}. {d.jugadores[falso][0]} nunca {pronombre(fam)} ganó.",
        }


def gen_equipos_campeones(d: Datos, dif: str, rng: random.Random, n: int):
    # Candidatos a "falso": clubes/selecciones con jugadores famosos que nunca lo ganaron
    fama_equipo: dict[str, int] = defaultdict(int)
    for j, eqs in d.equipos_de.items():
        if j in d.jugadores:
            for e in eqs:
                fama_equipo[e] += d.jugadores[j][1]
    ganadores_de_algo = {e for fam in d.campeones for e in d.campeones[fam]}
    for fam in rng.sample(sorted(TORNEOS_CLUBES | TORNEOS_SELECCIONES), k=len(TORNEOS_CLUBES | TORNEOS_SELECCIONES)):
        if fam not in d.nombre_familia:
            continue
        campeones = d.campeones.get(fam, {})
        if len(campeones) < 4:
            continue
        veces_falsa: dict[str, int] = defaultdict(int)   # para no repetir siempre la misma falsa
        de_selecciones = fam in TORNEOS_SELECCIONES
        # Mismo tipo de equipo que los campeones (club o selección)
        tipo_valido = {e for e in fama_equipo if e in d.nombre_equipo}
        for _ in range(n):
            # Fácil: campeones con más títulos (más conocidos); difícil: cualquiera
            orden = sorted(campeones, key=lambda e: -len(campeones[e]))
            pool = orden[:8] if dif == "facil" else orden
            if len(pool) < 4:
                break
            verdaderos = rng.sample(pool, 4)
            # Falsa creíble: mismo tipo de equipo, del mismo continente que algún campeón
            # (para la Copa América, una sudamericana), y conocida (pasaron muchos reconocidos)
            conts = {d.continente_equipo.get(e) for e in campeones} - {None}
            candidatos = [e for e in tipo_valido if e not in d.campeones_registros.get(fam, set())
                          and es_seleccion(d, e) == de_selecciones
                          and d.continente_equipo.get(e) in conts
                          and fama_equipo[e] >= FAMA_MINIMA_EQUIPO]
            if not candidatos:
                break

            def credibilidad(e: str) -> float:
                s = 0.6 if e in ganadores_de_algo else 0.0     # ganó otro de los torneos relevantes
                return s + min(fama_equipo[e] / 5_000_000, 0.4)  # muchos jugadores famosos pasaron por ahí

            puntuados = sorted(((credibilidad(e), e) for e in candidatos), reverse=True)
            minimo, maximo = {"facil": (0.0, 0.5), "intermedio": (0.2, 1.0), "dificil": (0.6, 1.0)}[dif]
            puntuados = [(s, e) for s, e in puntuados if minimo <= s <= maximo and veces_falsa[e] < 2][:6]
            if not puntuados:
                break
            _, falso = rng.choice(puntuados)
            veces_falsa[falso] += 1
            nombre = d.nombre_familia[fam]
            sujeto = "selecciones" if de_selecciones else "clubes"
            opciones = [{"texto": d.nombre_equipo[v], "qid": v, "verdadera": True} for v in verdaderos]
            opciones.append({"texto": d.nombre_equipo[falso], "qid": falso, "verdadera": False})
            rng.shuffle(opciones)
            veces = lambda v: len(campeones[v])  # noqa: E731
            yield {
                "clave": f"equipos_campeones:{fam}:{falso}:{','.join(sorted(verdaderos))}",
                "tipo": "equipos_campeones",
                "dificultad": dif,
                "afirmacion": f"Todas estas {sujeto} ganaron {TEXTO[fam][0]}" if de_selecciones
                              else f"Todos estos {sujeto} ganaron {TEXTO[fam][0]}",
                "protagonista": {"tipo": "titulo", "qid": fam, "nombre": nombre},
                "opciones": opciones,
                "explicacion": lista([f"{d.nombre_equipo[v]} ({veces(v)} {'vez' if veces(v) == 1 else 'veces'})"
                                      for v in verdaderos])
                               + f" ganaron {TEXTO[fam][0]}. {d.nombre_equipo[falso]} nunca {pronombre(fam)} ganó.",
            }


def es_seleccion(d: Datos, equipo: str) -> bool | None:
    """True = selección mayor, False = club, None = otro (juvenil, desconocido): nunca se usa."""
    return {"seleccion": True, "club": False}.get(d.tipo_equipo.get(equipo, ""))


def gen_titulos_de_jugador(d: Datos, dif: str, rng: random.Random, n: int):
    del_tramo = sorted(tramo(d, dif))
    rng.shuffle(del_tramo)
    # Años en que cada competición existió (según la base) para que el falso sea posible
    anios_de: dict[str, set[int]] = defaultdict(set)
    for ts in d.titulos.values():
        for fam, a in ts:
            anios_de[fam].add(a)
    for fam, eqs in d.campeones.items():
        for anios in eqs.values():
            anios_de[fam] |= set(anios)
    hechas = 0
    for j in del_tramo:
        if hechas >= n:
            return
        propios = sorted(d.titulos.get(j, ()))
        if len(propios) < 4 or j not in d.jugadores:
            continue
        # Preferir variedad de competiciones entre las verdaderas
        por_fam: dict[str, list] = defaultdict(list)
        for t in propios:
            por_fam[t[0]].append(t)
        verdaderos = []
        while len(verdaderos) < 4:
            for fam in list(por_fam):
                if por_fam[fam] and len(verdaderos) < 4:
                    verdaderos.append(por_fam[fam].pop(rng.randrange(len(por_fam[fam]))))
        ini, fin = d.anios_activo.get(j, (min(a for _, a in propios) - 5, max(a for _, a in propios) + 2))
        familias_suyas = {f for f, _ in propios}
        candidatos = []
        for fam in FAMILIAS:
            if fam not in d.nombre_familia:
                continue
            for a in anios_de[fam]:
                if ini <= a <= fin and not algun_registro(d, j, fam, a):
                    # Más creíble: una competición que sí ganó otras veces, en sus años de carrera
                    s = 0.6 if fam in familias_suyas else 0.3
                    if any(abs(a - b) <= 2 for f2, b in propios if f2 == fam):
                        s += 0.3
                    candidatos.append((s, fam, a))
        minimo, maximo = {"facil": (0.0, 0.6), "intermedio": (0.3, 0.9), "dificil": (0.6, 1.0)}[dif]
        candidatos = [c for c in candidatos if minimo <= c[0] <= maximo]
        if not candidatos:
            continue
        _, ffam, fanio = rng.choice(sorted(candidatos, reverse=True)[:6])
        texto = lambda fam, a: f"{d.nombre_familia[fam]} {texto_edicion(fam, a)}"  # noqa: E731
        nombre = d.jugadores[j][0]
        opciones = [{"texto": texto(f, a), "qid": f"{f}:{a}", "verdadera": True} for f, a in verdaderos]
        opciones.append({"texto": texto(ffam, fanio), "qid": f"{ffam}:{fanio}", "verdadera": False})
        rng.shuffle(opciones)
        hechas += 1
        yield {
            "clave": f"titulos_de_jugador:{j}:{ffam}:{fanio}",
            "tipo": "titulos_de_jugador",
            "dificultad": dif,
            "afirmacion": f"{nombre} ganó todos estos títulos",
            "protagonista": {"tipo": "jugador", "qid": j, "nombre": nombre},
            "opciones": opciones,
            "explicacion": f"{nombre} ganó {lista([texto(f, a) for f, a in verdaderos])}. "
                           f"No ganó {texto(ffam, fanio)}.",
        }
