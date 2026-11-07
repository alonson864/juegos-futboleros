"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Avatar, CreditosFotos } from "../../componentes/Foto";
import type { Categoria, Item } from "./tipos";

/** Jugadores por categoría: con 10 jugadores hay 9 comparaciones. */
const POR_CATEGORIA = 10;
const MAX_JUGADORES = 4;

const CATEGORIAS: {
  id: Categoria;
  nombre: string;
  icono: string;
  unidad: string;
  pregunta: (a: string, b: string) => string;
  fuente: string;
  limite: number; // cuánto puede crecer o achicarse el número entre un jugador y el siguiente
}[] = [
  {
    id: "goles",
    nombre: "Goles",
    icono: "⚽",
    unidad: "goles",
    pregunta: (a, b) => `¿${b} hizo más o menos goles que ${a}?`,
    fuente:
      "Goles en liga con sus clubes más los goles con su selección mayor, según la ficha de cada jugador en Wikipedia (en inglés).",
    limite: 1.3,
  },
  {
    id: "asistencias",
    nombre: "Asistencias",
    icono: "🎯",
    unidad: "asistencias en la Premier",
    pregunta: (a, b) => `¿${b} dio más o menos asistencias en la Premier League que ${a}?`,
    fuente: "Asistencias oficiales en la Premier League, según el artículo de récords de la Premier League en Wikipedia (en inglés).",
    limite: 1.3,
  },
  {
    id: "titulos",
    nombre: "Títulos",
    icono: "🏆",
    unidad: "títulos",
    pregunta: (a, b) => `¿${b} ganó más o menos títulos que ${a}?`,
    fuente:
      "Títulos con sus clubes y su selección mayor, según el palmarés de Wikipedia (en inglés). No cuentan premios individuales ni títulos juveniles.",
    limite: 1.35,
  },
  {
    id: "fichajes",
    nombre: "Fichajes más caros",
    icono: "💰",
    unidad: "millones de euros",
    pregunta: (a, b) => `¿El fichaje de ${b} costó más o menos que el de ${a}?`,
    fuente: "Monto de cada fichaje en millones de euros, según la lista de fichajes más caros de la historia de Wikipedia (en inglés).",
    limite: 1.25,
  },
  {
    id: "partidos",
    nombre: "Partidos jugados",
    icono: "👟",
    unidad: "partidos",
    pregunta: (a, b) => `¿${b} jugó más o menos partidos que ${a}?`,
    fuente:
      "Partidos en liga con sus clubes más los partidos con su selección mayor, según la ficha de cada jugador en Wikipedia (en inglés).",
    limite: 1.2,
  },
];
const INFO = Object.fromEntries(CATEGORIAS.map((c) => [c.id, c])) as Record<Categoria, (typeof CATEGORIAS)[number]>;

const COLOR = [
  { fondo: "bg-cancha", sobre: "text-sobre-cancha", texto: "text-cancha", borde: "border-cancha" },
  { fondo: "bg-rival", sobre: "text-sobre-rival", texto: "text-rival", borde: "border-rival" },
  { fondo: "bg-grupo-4", sobre: "text-sobre-grupo", texto: "text-grupo-4", borde: "border-grupo-4" },
  { fondo: "bg-tarjeta", sobre: "text-sobre-grupo", texto: "text-tinta", borde: "border-tarjeta" },
];

const enteros = new Intl.NumberFormat("es");
const decimales = new Intl.NumberFormat("es", { maximumFractionDigits: 1 });

function mostrar(valor: number, categoria: Categoria) {
  return categoria === "fichajes" ? `${decimales.format(valor)} M€` : enteros.format(valor);
}

function mezclar<T>(lista: T[]): T[] {
  const copia = [...lista];
  for (let i = copia.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copia[i], copia[j]] = [copia[j], copia[i]];
  }
  return copia;
}

/**
 * Cadena de jugadores donde cada número es parecido al anterior (sin saltos obvios),
 * sin repetir jugador ni empates. Si no se puede con el límite de la categoría, se afloja un poco.
 */
function armarCadena(pool: Item[], categoria: Categoria): Item[] {
  const distintos = new Set(pool.map((i) => i.jugador_qid)).size;
  const largo = Math.min(POR_CATEGORIA, distintos);
  const casiIguales = pool.length > 30; // con muchos jugadores, se evitan números casi idénticos

  for (let limite = INFO[categoria].limite; limite < 6; limite *= 1.15) {
    for (let intento = 0; intento < 30; intento++) {
      let presupuesto = 3000;
      const cadena: Item[] = [];
      const usados = new Set<string>();

      const buscar = (): boolean => {
        if (cadena.length === largo) return true;
        if (--presupuesto <= 0) return false;
        const actual = cadena[cadena.length - 1];
        let candidatos = pool.filter((i) => !usados.has(i.jugador_qid));
        if (actual) {
          candidatos = candidatos.filter((i) => {
            if (i.valor === actual.valor) return false;
            const r = Math.max(i.valor, actual.valor) / Math.min(i.valor, actual.valor);
            return r <= limite && (!casiIguales || r >= 1.03);
          });
          // Al azar sube o baja, para que la respuesta no sea siempre la misma
          const sube = Math.random() < 0.5;
          const mezclados = mezclar(candidatos);
          candidatos = [
            ...mezclados.filter((i) => i.valor > actual.valor === sube),
            ...mezclados.filter((i) => i.valor > actual.valor !== sube),
          ].slice(0, 12);
        } else {
          candidatos = mezclar(candidatos).slice(0, 5);
        }
        for (const c of candidatos) {
          cadena.push(c);
          usados.add(c.jugador_qid);
          if (buscar()) return true;
          cadena.pop();
          usados.delete(c.jugador_qid);
        }
        return false;
      };

      if (buscar()) return cadena;
    }
  }
  return mezclar(pool).slice(0, largo);
}

type Respuesta = { eleccion: "mas" | "menos"; acierto: boolean };
type Fase = "nombres" | "juego" | "pausa" | "final";

export default function MayorOMenor({ items }: { items: Item[] }) {
  const disponibles = CATEGORIAS.filter((c) => items.filter((i) => i.categoria === c.id).length >= 2);

  const [fase, setFase] = useState<Fase>("nombres");
  const [nombres, setNombres] = useState<string[]>(["", ""]);
  const [elegidas, setElegidas] = useState<Categoria[]>(disponibles.map((c) => c.id));
  const [jugadores, setJugadores] = useState<string[]>([]);
  const [cadenas, setCadenas] = useState<{ categoria: Categoria; items: Item[] }[]>([]);
  const [cat, setCat] = useState(0);
  const [paso, setPaso] = useState(0);
  const [turno, setTurno] = useState(0);
  const [puntos, setPuntos] = useState<number[]>([]);
  const [racha, setRacha] = useState(0);
  const [respuesta, setRespuesta] = useState<Respuesta | null>(null);

  function empezar() {
    const lista = nombres.map((n, i) => n.trim() || `Jugador ${i + 1}`);
    const orden = CATEGORIAS.map((c) => c.id).filter((id) => elegidas.includes(id));
    setJugadores(lista);
    setCadenas(orden.map((categoria) => ({ categoria, items: armarCadena(items.filter((i) => i.categoria === categoria), categoria) })));
    setPuntos(lista.map(() => 0));
    setCat(0);
    setPaso(0);
    setTurno(0);
    setRacha(0);
    setRespuesta(null);
    setFase("juego");
  }

  const cadena = cadenas[cat];
  const izquierda = cadena?.items[paso];
  const derecha = cadena?.items[paso + 1];

  const responder = useCallback(
    (eleccion: "mas" | "menos") => {
      if (fase !== "juego" || respuesta || !izquierda || !derecha) return;
      const acierto = eleccion === "mas" ? derecha.valor > izquierda.valor : derecha.valor < izquierda.valor;
      setRespuesta({ eleccion, acierto });
      if (acierto) {
        setPuntos((p) => p.map((x, i) => (i === turno ? x + 1 : x)));
        setRacha((r) => r + 1);
      }
    },
    [fase, respuesta, izquierda, derecha, turno],
  );

  const avanzar = useCallback(() => {
    if (!respuesta || !cadena) return;
    if (!respuesta.acierto) {
      // Falló: sigue el próximo jugador desde donde quedó
      setTurno((t) => (t + 1) % jugadores.length);
      setRacha(0);
    }
    setRespuesta(null);
    if (paso + 2 < cadena.items.length) {
      setPaso(paso + 1);
    } else if (cat + 1 < cadenas.length) {
      setFase("pausa");
    } else {
      setFase("final");
    }
  }, [respuesta, cadena, paso, cat, cadenas.length, jugadores.length]);

  // Si acertó, sigue solo después de ver el número
  useEffect(() => {
    if (!respuesta?.acierto) return;
    const t = setTimeout(avanzar, 1600);
    return () => clearTimeout(t);
  }, [respuesta, avanzar]);

  // Teclado: ↑ más, ↓ menos, Enter para seguir
  useEffect(() => {
    if (fase !== "juego") return;
    function tecla(e: KeyboardEvent) {
      if (e.key === "ArrowUp") {
        e.preventDefault();
        responder("mas");
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        responder("menos");
      } else if (e.key === "Enter" && respuesta) {
        e.preventDefault();
        avanzar();
      }
    }
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, [fase, responder, avanzar, respuesta]);

  // ---------------------------------------------------------------- Nombres
  if (fase === "nombres") {
    return (
      <form
        className="mt-6 flex flex-col gap-5 lg:mt-10 lg:gap-7"
        onSubmit={(e) => {
          e.preventDefault();
          if (elegidas.length > 0) empezar();
        }}
      >
        <div className="rounded-2xl bg-superficie-2 p-4 text-sm lg:p-6 lg:text-base">
          <p className="font-display text-lg font-bold uppercase lg:text-2xl">Cómo se juega</p>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-tenue">
            <li>Aparecen dos jugadores: el de la izquierda muestra su número.</li>
            <li>
              Adivina si el de la derecha tiene <strong className="text-tinta">más</strong> o{" "}
              <strong className="text-tinta">menos</strong>. Cada acierto vale un punto y sigues jugando.
            </li>
            <li>Si fallas, le toca al siguiente jugador, que retoma desde donde fallaste.</li>
            <li>
              Cada categoría tiene {POR_CATEGORIA} jugadores. Al terminar todas, gana el que tiene más puntos.
            </li>
          </ol>
        </div>

        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 font-display text-base font-bold uppercase lg:text-lg">Categorías</legend>
          <div className="flex flex-wrap gap-2 lg:gap-3">
            {disponibles.map((c) => {
              const activa = elegidas.includes(c.id);
              return (
                <button
                  key={c.id}
                  type="button"
                  aria-pressed={activa}
                  onClick={() => setElegidas(activa ? elegidas.filter((x) => x !== c.id) : [...elegidas, c.id])}
                  className={`flex items-center gap-2 rounded-full border-2 px-4 py-2 font-display text-base font-bold uppercase tracking-wide transition lg:px-5 lg:py-2.5 lg:text-lg ${
                    activa ? "border-cancha bg-cancha text-sobre-cancha" : "border-borde bg-superficie text-tenue hover:border-tinta/30"
                  }`}
                >
                  <span aria-hidden="true">{c.icono}</span> {c.nombre}
                </button>
              );
            })}
          </div>
        </fieldset>

        <fieldset className="flex flex-col gap-3">
          <legend className="mb-2 font-display text-base font-bold uppercase lg:text-lg">Jugadores</legend>
          <div className="grid gap-3 lg:grid-cols-2 lg:gap-4">
            {nombres.map((n, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className={`h-10 w-2 shrink-0 rounded-full ${COLOR[i].fondo}`} aria-hidden="true" />
                <input
                  value={n}
                  onChange={(e) => setNombres(nombres.map((x, j) => (j === i ? e.target.value.slice(0, 20) : x)))}
                  placeholder={`Jugador ${i + 1}`}
                  aria-label={`Nombre del jugador ${i + 1}`}
                  autoComplete="off"
                  autoFocus={i === 0}
                  className="min-w-0 flex-1 rounded-2xl border-2 border-borde bg-superficie px-4 py-3 text-lg font-semibold outline-none placeholder:font-normal placeholder:text-tenue focus:border-tinta/40 lg:px-5 lg:py-3.5 lg:text-xl"
                />
                {nombres.length > 1 && (
                  <button
                    type="button"
                    onClick={() => setNombres(nombres.filter((_, j) => j !== i))}
                    aria-label={`Quitar al jugador ${i + 1}`}
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-xl text-tenue hover:bg-superficie-2 hover:text-tinta"
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>
          {nombres.length < MAX_JUGADORES && (
            <button
              type="button"
              onClick={() => setNombres([...nombres, ""])}
              className="self-start rounded-full border border-dashed border-borde px-4 py-2 text-sm font-semibold text-tenue hover:border-tinta/40 hover:text-tinta"
            >
              + Agregar jugador
            </button>
          )}
        </fieldset>

        {elegidas.length === 0 && <p className="text-center text-sm text-roja">Elige al menos una categoría.</p>}
        <button
          type="submit"
          disabled={elegidas.length === 0}
          className="mt-1 rounded-full bg-cancha px-6 py-3 font-display text-xl font-bold uppercase tracking-wide text-sobre-cancha hover:bg-cancha-fuerte active:scale-[0.99] disabled:opacity-50 lg:self-center lg:px-16 lg:py-4 lg:text-2xl"
        >
          ¡A jugar!
        </button>
      </form>
    );
  }

  // ---------------------------------------------------------------- Final
  if (fase === "final") {
    const max = Math.max(...puntos);
    const ganadores = jugadores.filter((_, i) => puntos[i] === max);
    return (
      <section className="aparecer mt-6 flex flex-col items-center gap-4 rounded-3xl border border-borde bg-superficie p-6 text-center shadow-sm lg:mx-auto lg:mt-10 lg:w-full lg:max-w-2xl lg:gap-6 lg:p-12">
        <p className="font-display text-lg font-bold uppercase text-tenue lg:text-2xl">Final del partido</p>
        <p className="font-display text-4xl leading-none font-extrabold uppercase lg:text-7xl">
          {jugadores.length === 1
            ? `${max} ${max === 1 ? "acierto" : "aciertos"}`
            : ganadores.length > 1
              ? "¡Empate!"
              : `¡Ganó ${ganadores[0]}!`}
        </p>
        <Marcador jugadores={jugadores} puntos={puntos} activo={-1} ordenar />
        <div className="mt-2 flex flex-wrap justify-center gap-2 lg:gap-3">
          <button
            type="button"
            onClick={empezar}
            className="rounded-full bg-cancha px-6 py-2.5 font-display text-lg font-bold uppercase tracking-wide text-sobre-cancha hover:bg-cancha-fuerte lg:px-10 lg:py-3 lg:text-xl"
          >
            Revancha
          </button>
          <button
            type="button"
            onClick={() => setFase("nombres")}
            className="rounded-full border border-borde bg-superficie px-5 py-2.5 font-display text-lg font-bold uppercase tracking-wide hover:bg-superficie-2 lg:px-8 lg:py-3 lg:text-xl"
          >
            Cambiar jugadores
          </button>
        </div>
      </section>
    );
  }

  // ---------------------------------------------------------------- Entre categorías
  if (fase === "pausa") {
    const proxima = INFO[cadenas[cat + 1].categoria];
    return (
      <section className="aparecer mt-6 flex flex-col items-center gap-4 rounded-3xl border border-borde bg-superficie p-6 text-center shadow-sm lg:mx-auto lg:mt-10 lg:w-full lg:max-w-2xl lg:gap-6 lg:p-12">
        <p className="font-display text-lg font-bold uppercase text-tenue lg:text-2xl">
          Fin de {INFO[cadena.categoria].nombre.toLowerCase()}
        </p>
        <p className="font-display text-3xl leading-none font-extrabold uppercase lg:text-5xl">
          Ahora: <span aria-hidden="true">{proxima.icono}</span> {proxima.nombre}
        </p>
        <Marcador jugadores={jugadores} puntos={puntos} activo={turno} />
        {jugadores.length > 1 && (
          <p className={`font-display text-lg font-extrabold uppercase ${COLOR[turno].texto}`}>Empieza {jugadores[turno]}</p>
        )}
        <button
          type="button"
          autoFocus
          onClick={() => {
            setCat(cat + 1);
            setPaso(0);
            setFase("juego");
          }}
          className="rounded-full bg-cancha px-8 py-3 font-display text-xl font-bold uppercase tracking-wide text-sobre-cancha hover:bg-cancha-fuerte lg:px-12"
        >
          Siguiente categoría →
        </button>
      </section>
    );
  }

  // ---------------------------------------------------------------- Juego
  const info = INFO[cadena.categoria];
  const siguiente = (turno + 1) % jugadores.length;

  return (
    <section className="mt-5 flex flex-col gap-4 lg:mt-8 lg:grid lg:grid-cols-[1fr_18rem] lg:items-start lg:gap-10">
      <div className="flex flex-col gap-4">
        <div className="grano relative overflow-hidden rounded-3xl bg-noche p-5 text-white shadow-lg lg:p-7">
          <div className="reflectores absolute inset-0" aria-hidden="true" />
          <p className="relative font-display text-sm font-bold uppercase tracking-[0.2em] text-tarjeta">
            {info.icono} {info.nombre} · Categoría {cat + 1} de {cadenas.length}
          </p>
          <h2 className="relative mt-1.5 font-display text-2xl leading-[1.05] font-extrabold uppercase lg:text-4xl">
            {info.pregunta(izquierda.nombre, derecha.nombre)}
          </h2>
        </div>

        <div key={`${cat}-${paso}`} className="grid grid-cols-2 gap-3 lg:gap-6">
          <Tarjeta item={izquierda} categoria={cadena.categoria} visible />
          <Tarjeta
            item={derecha}
            categoria={cadena.categoria}
            visible={Boolean(respuesta)}
            resultado={respuesta ? (respuesta.acierto ? "bien" : "mal") : undefined}
          >
            {!respuesta && (
              <div className="flex w-full flex-col gap-2 lg:gap-3">
                <button
                  type="button"
                  onClick={() => responder("mas")}
                  className="rounded-full bg-cancha px-3 py-2.5 font-display text-lg font-bold uppercase tracking-wide text-sobre-cancha hover:bg-cancha-fuerte active:scale-[0.98] lg:py-3 lg:text-2xl"
                >
                  ▲ Más
                </button>
                <button
                  type="button"
                  onClick={() => responder("menos")}
                  className="rounded-full bg-rival px-3 py-2.5 font-display text-lg font-bold uppercase tracking-wide text-sobre-rival hover:opacity-90 active:scale-[0.98] lg:py-3 lg:text-2xl"
                >
                  ▼ Menos
                </button>
              </div>
            )}
          </Tarjeta>
        </div>

        {respuesta && (
          <div
            className="aparecer flex flex-col gap-3 rounded-2xl bg-superficie-2 p-4 lg:flex-row lg:items-center lg:gap-6 lg:p-5"
            aria-live="polite"
          >
            <p
              className={`font-display text-xl font-extrabold uppercase lg:flex-1 lg:text-2xl ${
                respuesta.acierto ? "text-cancha" : "text-roja"
              }`}
            >
              {respuesta.acierto
                ? `¡Bien! +1 para ${jugadores[turno]}`
                : jugadores.length > 1
                  ? `Fallaste, ${jugadores[turno]}. Le toca a ${jugadores[siguiente]}`
                  : "Fallaste. Sigue intentando"}
            </p>
            {!respuesta.acierto && (
              <button
                type="button"
                onClick={avanzar}
                autoFocus
                className="self-end rounded-full bg-cancha px-6 py-2.5 font-display text-base font-bold uppercase tracking-wide whitespace-nowrap text-sobre-cancha hover:bg-cancha-fuerte lg:self-center lg:py-3 lg:text-lg"
              >
                {jugadores.length > 1 ? `Sigue ${jugadores[siguiente]} →` : "Seguir →"}
              </button>
            )}
          </div>
        )}

        <div className="flex flex-col gap-1 text-xs text-tenue">
          <p>Dato: {info.fuente}</p>
          <CreditosFotos fotos={[izquierda, derecha]} />
        </div>
      </div>

      <aside className="flex flex-col gap-3 lg:sticky lg:top-24 lg:rounded-3xl lg:border lg:border-borde lg:bg-superficie lg:p-5 lg:shadow-sm">
        <p className="font-display text-lg font-bold uppercase">Marcador</p>
        <Marcador jugadores={jugadores} puntos={puntos} activo={turno} />
        {jugadores.length > 1 && (
          <p className={`font-display text-lg font-extrabold uppercase ${COLOR[turno].texto}`}>Turno de {jugadores[turno]}</p>
        )}
        <p className="text-sm text-tenue">
          Racha: <strong className="text-tinta">{racha}</strong> · Jugador {paso + 2} de {cadena.items.length}
        </p>
        <div className="h-1.5 overflow-hidden rounded-full bg-superficie-2">
          <div
            className="h-full rounded-full bg-cancha transition-all"
            style={{ width: `${((paso + 1) / (cadena.items.length - 1)) * 100}%` }}
          />
        </div>
        <p className="hidden text-xs text-tenue lg:block">Atajos: ↑ más · ↓ menos · Enter para seguir</p>
      </aside>
    </section>
  );
}

function Tarjeta({
  item,
  categoria,
  visible,
  resultado,
  children,
}: {
  item: Item;
  categoria: Categoria;
  visible: boolean;
  resultado?: "bien" | "mal";
  children?: ReactNode;
}) {
  const borde =
    resultado === "bien" ? "border-2 border-cancha bg-cancha/10" : resultado === "mal" ? "border-2 border-roja bg-roja/10" : "border border-borde bg-superficie";
  return (
    <div
      className={`aparecer flex flex-col items-center gap-2 rounded-3xl p-3 text-center shadow-sm transition sm:p-4 lg:gap-3 lg:p-7 ${borde}`}
    >
      <Avatar nombre={item.nombre} foto={item.foto} tamano={84} className="lg:hidden" />
      <Avatar nombre={item.nombre} foto={item.foto} tamano={168} className="hidden lg:inline-flex" />
      <p className="font-display text-lg leading-tight font-extrabold uppercase lg:text-3xl">{item.nombre}</p>
      {categoria === "fichajes" && item.detalle && <p className="text-xs text-tenue lg:text-sm">{item.detalle}</p>}
      <div className="flex min-h-16 flex-col items-center justify-center lg:min-h-24">
        {visible ? (
          <>
            <p className="digitos font-display text-4xl leading-none font-extrabold lg:text-7xl">{mostrar(item.valor, categoria)}</p>
            <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-tenue lg:text-sm">
              {INFO[categoria].unidad}
            </p>
          </>
        ) : (
          !children && <p className="font-display text-5xl font-extrabold text-tenue lg:text-7xl">?</p>
        )}
        {!visible && children}
      </div>
    </div>
  );
}

function Marcador({
  jugadores,
  puntos,
  activo,
  ordenar = false,
}: {
  jugadores: string[];
  puntos: number[];
  activo: number;
  ordenar?: boolean;
}) {
  const filas = jugadores.map((nombre, i) => ({ nombre, i, puntos: puntos[i] }));
  if (ordenar) filas.sort((a, b) => b.puntos - a.puntos);
  return (
    <div className="grid w-full grid-cols-2 gap-2 lg:grid-cols-1">
      {filas.map(({ nombre, i, puntos: p }) => (
        <div
          key={i}
          className={`flex items-center justify-between gap-2 rounded-2xl px-4 py-2.5 transition lg:py-3 ${
            activo === i ? `${COLOR[i].fondo} ${COLOR[i].sobre} shadow-md` : `border-2 ${COLOR[i].borde} bg-superficie`
          }`}
        >
          <span className="truncate font-semibold lg:text-lg">{nombre}</span>
          <span className="font-display text-3xl leading-none font-extrabold lg:text-4xl">{p}</span>
        </div>
      ))}
    </div>
  );
}
