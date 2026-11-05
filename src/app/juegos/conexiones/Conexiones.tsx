"use client";

import { useState, useSyncExternalStore } from "react";
import { Avatar, CreditosFotos } from "../../componentes/Foto";
import type { Grupo, Puzzle } from "./tipos";

const MAX_ERRORES = 4;

const COLORES: Record<number, string> = {
  1: "bg-grupo-1",
  2: "bg-grupo-2",
  3: "bg-grupo-3",
  4: "bg-grupo-4",
};

// La fecha solo se conoce en el navegador; en el servidor devolvemos null.
const suscribir = () => () => {};
function hoyLocal(): string {
  const d = new Date();
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mes}-${dia}`;
}

// Último puzzle cuya fecha ya llegó; si ninguno llegó todavía, el primero.
function indiceDelDia(puzzles: Puzzle[], hoy: string): number {
  let indice = 0;
  puzzles.forEach((p, i) => {
    if (p.fecha <= hoy) indice = i;
  });
  return indice;
}

function formatearFecha(fecha: string): string {
  return new Date(`${fecha}T00:00:00Z`).toLocaleDateString("es", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

// Mezcla con semilla: todos ven el mismo orden inicial para el mismo puzzle.
function mezclar<T>(lista: T[], semilla?: number): T[] {
  let s = semilla ?? Math.floor(Math.random() * 2 ** 32);
  const azar = () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const copia = [...lista];
  for (let i = copia.length - 1; i > 0; i--) {
    const j = Math.floor(azar() * (i + 1));
    [copia[i], copia[j]] = [copia[j], copia[i]];
  }
  return copia;
}

export default function Conexiones({ puzzles }: { puzzles: Puzzle[] }) {
  const hoy = useSyncExternalStore(suscribir, hoyLocal, () => null);
  const [elegido, setElegido] = useState<number | null>(null);

  if (hoy === null) {
    return <p className="mt-10 text-center text-tenue">Cargando…</p>;
  }

  const indice = elegido ?? indiceDelDia(puzzles, hoy);
  const puzzle = puzzles[indice];

  return (
    <>
      <nav className="mt-5 flex items-center justify-between gap-2 rounded-full border border-borde bg-superficie p-1 text-sm">
        <button
          type="button"
          onClick={() => setElegido(indice - 1)}
          disabled={indice === 0}
          className="rounded-full px-3 py-1.5 font-medium text-cancha hover:bg-superficie-2 disabled:text-tenue disabled:opacity-40 disabled:hover:bg-transparent"
        >
          ←<span className="sr-only sm:not-sr-only"> Anterior</span>
        </button>
        <span className="text-center leading-tight">
          <span className="block font-display text-base font-bold uppercase">Puzzle #{puzzle.id}</span>
          <span className="block text-xs text-tenue">{formatearFecha(puzzle.fecha)}</span>
        </span>
        <button
          type="button"
          onClick={() => setElegido(indice + 1)}
          disabled={indice === puzzles.length - 1}
          className="rounded-full px-3 py-1.5 font-medium text-cancha hover:bg-superficie-2 disabled:text-tenue disabled:opacity-40 disabled:hover:bg-transparent"
        >
          <span className="sr-only sm:not-sr-only">Siguiente </span>→
        </button>
      </nav>
      <Juego key={puzzle.id} puzzle={puzzle} />
    </>
  );
}

function Juego({ puzzle }: { puzzle: Puzzle }) {
  const [orden, setOrden] = useState(() =>
    mezclar(
      puzzle.grupos.flatMap((g) => g.jugadores),
      puzzle.id,
    ),
  );
  const [seleccion, setSeleccion] = useState<string[]>([]);
  const [resueltos, setResueltos] = useState<Grupo[]>([]);
  const [errores, setErrores] = useState(0);
  const [intentos, setIntentos] = useState<string[]>([]);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [sacudidas, setSacudidas] = useState(0);

  const perdio = errores >= MAX_ERRORES;
  const gano = resueltos.length === puzzle.grupos.length;
  const terminado = perdio || gano;

  const gruposVisibles = perdio
    ? [...resueltos, ...puzzle.grupos.filter((g) => !resueltos.includes(g))]
    : resueltos;
  const restantes = terminado
    ? []
    : orden.filter((j) => !resueltos.some((g) => g.jugadores.includes(j)));

  function alternar(jugador: string) {
    setMensaje(null);
    if (seleccion.includes(jugador)) {
      setSeleccion(seleccion.filter((j) => j !== jugador));
    } else if (seleccion.length < 4) {
      setSeleccion([...seleccion, jugador]);
    }
  }

  function enviar() {
    const clave = [...seleccion].sort().join("|");
    if (intentos.includes(clave)) {
      setMensaje("Ya probaste esa combinación.");
      return;
    }
    setIntentos([...intentos, clave]);

    const acierto = puzzle.grupos.find((g) =>
      g.jugadores.every((j) => seleccion.includes(j)),
    );
    if (acierto) {
      setResueltos([...resueltos, acierto]);
      setSeleccion([]);
      setMensaje(null);
      return;
    }

    const nuevosErrores = errores + 1;
    setErrores(nuevosErrores);
    setSacudidas(sacudidas + 1);
    const casi = puzzle.grupos.some(
      (g) => g.jugadores.filter((j) => seleccion.includes(j)).length === 3,
    );
    setMensaje(casi && nuevosErrores < MAX_ERRORES ? "¡Te faltó uno!" : "No es un grupo.");
  }

  const todos = puzzle.grupos.flatMap((g) => g.jugadores.map((j, i) => ({ nombre: j, foto: g.fotos?.[i] ?? null })));
  const fotoDe = new Map(todos.map((t) => [t.nombre, t.foto]));

  return (
    <section className="mt-5 flex flex-col gap-2">
      {gruposVisibles.map((g) => (
        <div
          key={g.categoria}
          className={`aparecer rounded-2xl px-3 py-3 text-center text-sobre-grupo lg:py-5 ${COLORES[g.dificultad]}`}
        >
          <p className="font-display text-lg leading-tight font-extrabold uppercase lg:text-2xl">{g.categoria}</p>
          <ul className="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-2 text-sm lg:text-base">
            {g.jugadores.map((j) => (
              <li key={j} className="flex items-center gap-1.5">
                <Avatar nombre={j} foto={fotoDe.get(j)} tamano={36} className="hidden ring-black/10 sm:inline-flex" />
                {j}
              </li>
            ))}
          </ul>
        </div>
      ))}

      {restantes.length > 0 && (
        <div key={sacudidas} className={`grid grid-cols-4 gap-2 lg:gap-3 ${sacudidas > 0 ? "sacudir" : ""}`}>
          {restantes.map((jugador) => {
            const activo = seleccion.includes(jugador);
            return (
              <button
                key={jugador}
                type="button"
                onClick={() => alternar(jugador)}
                aria-pressed={activo}
                className={`flex h-28 flex-col items-center justify-center gap-1.5 rounded-2xl px-1 text-center font-display text-[11px] leading-[1.05] font-bold uppercase break-words hyphens-auto transition active:scale-95 sm:h-32 sm:text-xs lg:h-48 lg:gap-2.5 lg:rounded-3xl lg:px-3 lg:text-base ${
                  activo
                    ? "bg-tinta text-tiza shadow-inner"
                    : "border border-borde bg-superficie text-tinta shadow-sm hover:bg-superficie-2"
                }`}
              >
                {/* Foto grande y el nombre más chico debajo */}
                <Avatar nombre={jugador} foto={fotoDe.get(jugador)} tamano={52} className="lg:hidden" />
                <Avatar nombre={jugador} foto={fotoDe.get(jugador)} tamano={104} className="hidden lg:inline-flex" />
                <span className="line-clamp-2">{jugador}</span>
              </button>
            );
          })}
        </div>
      )}

      <p
        className={`flex min-h-8 items-center justify-center text-center text-sm font-semibold ${
          gano ? "text-cancha" : perdio ? "text-roja" : "text-tinta"
        }`}
        aria-live="polite"
      >
        {gano
          ? "¡Golazo! Encontraste los 4 grupos."
          : perdio
            ? "Se acabaron los intentos. Estas eran las respuestas."
            : mensaje}
      </p>

      {!terminado && (
        <>
          <div className="flex items-center justify-center gap-2 text-sm text-tenue">
            <span>Errores disponibles</span>
            <span className="flex gap-1" aria-label={`${MAX_ERRORES - errores} de ${MAX_ERRORES}`}>
              {Array.from({ length: MAX_ERRORES }, (_, i) => (
                <span
                  key={i}
                  className={`h-4 w-3 rounded-[3px] transition-colors ${
                    i < MAX_ERRORES - errores ? "bg-tarjeta" : "bg-roja"
                  }`}
                />
              ))}
            </span>
          </div>
          <div className="mt-3 flex justify-center gap-2">
            <button
              type="button"
              onClick={() => setOrden(mezclar(orden))}
              className="rounded-full border border-borde bg-superficie px-4 py-2.5 font-display text-base font-bold uppercase tracking-wide hover:bg-superficie-2 lg:px-7 lg:py-3 lg:text-lg"
            >
              Mezclar
            </button>
            <button
              type="button"
              onClick={() => setSeleccion([])}
              disabled={seleccion.length === 0}
              className="rounded-full border border-borde bg-superficie px-4 py-2.5 font-display text-base font-bold uppercase tracking-wide hover:bg-superficie-2 disabled:opacity-40 lg:px-7 lg:py-3 lg:text-lg"
            >
              Borrar
            </button>
            <button
              type="button"
              onClick={enviar}
              disabled={seleccion.length !== 4}
              className="rounded-full bg-cancha px-5 py-2.5 font-display text-base font-bold uppercase tracking-wide text-sobre-cancha hover:bg-cancha-fuerte disabled:opacity-40 lg:px-9 lg:py-3 lg:text-lg"
            >
              Enviar
            </button>
          </div>
        </>
      )}
      <div className="mt-4">
        <CreditosFotos fotos={todos} />
      </div>
    </section>
  );
}
