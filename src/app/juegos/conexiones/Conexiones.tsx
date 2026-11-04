"use client";

import { useState, useSyncExternalStore } from "react";
import type { Grupo, Puzzle } from "./tipos";

const MAX_ERRORES = 4;

const COLORES: Record<number, string> = {
  1: "bg-yellow-300 text-yellow-950",
  2: "bg-green-400 text-green-950",
  3: "bg-sky-400 text-sky-950",
  4: "bg-purple-400 text-purple-950",
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
    return <p className="mt-8 text-center text-foreground/60">Cargando…</p>;
  }

  const indice = elegido ?? indiceDelDia(puzzles, hoy);
  const puzzle = puzzles[indice];

  return (
    <>
      <nav className="mt-5 flex items-center justify-between gap-2 text-sm">
        <button
          type="button"
          onClick={() => setElegido(indice - 1)}
          disabled={indice === 0}
          className="rounded-full px-3 py-1 hover:bg-foreground/10 disabled:opacity-30"
        >
          ← Anterior
        </button>
        <span className="text-center font-medium">
          #{puzzle.id} · {formatearFecha(puzzle.fecha)}
        </span>
        <button
          type="button"
          onClick={() => setElegido(indice + 1)}
          disabled={indice === puzzles.length - 1}
          className="rounded-full px-3 py-1 hover:bg-foreground/10 disabled:opacity-30"
        >
          Siguiente →
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
    const casi = puzzle.grupos.some(
      (g) => g.jugadores.filter((j) => seleccion.includes(j)).length === 3,
    );
    setMensaje(casi && nuevosErrores < MAX_ERRORES ? "¡Te faltó uno!" : "No es un grupo.");
  }

  return (
    <section className="mt-4 flex flex-col gap-2">
      {gruposVisibles.map((g) => (
        <div
          key={g.categoria}
          className={`rounded-xl px-3 py-3 text-center ${COLORES[g.dificultad]}`}
        >
          <p className="text-sm font-bold uppercase">{g.categoria}</p>
          <p className="mt-0.5 text-sm">{g.jugadores.join(", ")}</p>
        </div>
      ))}

      {restantes.length > 0 && (
        <div className="grid grid-cols-4 gap-2">
          {restantes.map((jugador) => {
            const activo = seleccion.includes(jugador);
            return (
              <button
                key={jugador}
                type="button"
                onClick={() => alternar(jugador)}
                aria-pressed={activo}
                className={`flex h-16 items-center justify-center rounded-xl px-1 text-center text-[11px] leading-tight font-semibold break-words hyphens-auto transition-colors sm:h-20 sm:text-sm ${
                  activo
                    ? "bg-slate-700 text-white dark:bg-slate-200 dark:text-slate-900"
                    : "bg-stone-200 text-stone-900 hover:bg-stone-300 dark:bg-stone-700 dark:text-stone-100 dark:hover:bg-stone-600"
                }`}
              >
                {jugador}
              </button>
            );
          })}
        </div>
      )}

      <p className="min-h-6 text-center text-sm font-medium" aria-live="polite">
        {gano
          ? "¡Bien jugado! Encontraste los 4 grupos."
          : perdio
            ? "Se acabaron los intentos. Estas eran las respuestas."
            : mensaje}
      </p>

      {!terminado && (
        <>
          <p className="text-center text-sm text-foreground/70">
            Errores disponibles:{" "}
            <span aria-label={`${MAX_ERRORES - errores} de ${MAX_ERRORES}`}>
              {"●".repeat(MAX_ERRORES - errores)}
              <span className="opacity-25">{"●".repeat(errores)}</span>
            </span>
          </p>
          <div className="mt-2 flex justify-center gap-2">
            <button
              type="button"
              onClick={() => setOrden(mezclar(orden))}
              className="rounded-full border border-foreground/30 px-4 py-2 text-sm font-medium"
            >
              Mezclar
            </button>
            <button
              type="button"
              onClick={() => setSeleccion([])}
              disabled={seleccion.length === 0}
              className="rounded-full border border-foreground/30 px-4 py-2 text-sm font-medium disabled:opacity-40"
            >
              Deseleccionar
            </button>
            <button
              type="button"
              onClick={enviar}
              disabled={seleccion.length !== 4}
              className="rounded-full bg-foreground px-4 py-2 text-sm font-medium text-background disabled:opacity-40"
            >
              Enviar
            </button>
          </div>
        </>
      )}
    </section>
  );
}
