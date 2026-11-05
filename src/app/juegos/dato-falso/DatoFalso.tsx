"use client";

import { useEffect, useState, type ReactNode } from "react";
import type { Dificultad, Pregunta } from "./tipos";

/** Preguntas por jugador según la dificultad, en el orden en que se juegan. */
const PLAN: { dificultad: Dificultad; rondas: number }[] = [
  { dificultad: "facil", rondas: 10 },
  { dificultad: "intermedio", rondas: 5 },
  { dificultad: "dificil", rondas: 5 },
];
const RONDAS = PLAN.reduce((total, p) => total + p.rondas, 0);

const NOMBRE_DIFICULTAD: Record<Dificultad, string> = {
  facil: "Fácil",
  intermedio: "Intermedio",
  dificil: "Difícil",
};

// Colores de cada jugador (de la paleta del sitio)
const COLOR = [
  { fondo: "bg-cancha", texto: "text-cancha", foco: "focus:border-cancha", sobre: "text-sobre-cancha" },
  { fondo: "bg-rival", texto: "text-rival", foco: "focus:border-rival", sobre: "text-sobre-rival" },
];

function mezclar<T>(lista: T[]): T[] {
  const copia = [...lista];
  for (let i = copia.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copia[i], copia[j]] = [copia[j], copia[i]];
  }
  return copia;
}

/**
 * Arma las 40 preguntas: en cada ronda, una para cada jugador y de la misma
 * dificultad. No repite preguntas y evita repetir protagonista.
 */
function armarPartida(preguntas: Pregunta[]): Pregunta[] | null {
  const usados = new Set<string>();
  const partida: Pregunta[] = [];
  for (const { dificultad, rondas } of PLAN) {
    const disponibles = mezclar(preguntas.filter((p) => p.dificultad === dificultad));
    const necesarias = rondas * 2;
    const elegidas: Pregunta[] = [];
    for (const p of disponibles) {
      if (elegidas.length === necesarias) break;
      const clave = p.protagonista?.qid ?? `id:${p.id}`;
      if (usados.has(clave)) continue;
      usados.add(clave);
      elegidas.push(p);
    }
    // Si no alcanzan protagonistas distintos, se completa con otras preguntas sin repetir.
    for (const p of disponibles) {
      if (elegidas.length === necesarias) break;
      if (!elegidas.includes(p)) elegidas.push(p);
    }
    if (elegidas.length < necesarias) return null;
    partida.push(...elegidas);
  }
  return partida;
}

function cuantasFaltan(preguntas: Pregunta[]): string[] {
  return PLAN.filter(
    ({ dificultad, rondas }) => preguntas.filter((p) => p.dificultad === dificultad).length < rondas * 2,
  ).map(({ dificultad }) => NOMBRE_DIFICULTAD[dificultad]);
}

export default function DatoFalso({ preguntas }: { preguntas: Pregunta[] }) {
  const [nombres, setNombres] = useState<[string, string]>(["", ""]);
  const [partida, setPartida] = useState<Pregunta[] | null>(null);
  const [actual, setActual] = useState(0);
  const [elegida, setElegida] = useState<string | null>(null);
  const [puntos, setPuntos] = useState<[number, number]>([0, 0]);

  const faltan = cuantasFaltan(preguntas);
  const pregunta = partida && actual < partida.length ? partida[actual] : null;
  const turno = actual % 2;
  const respondida = elegida !== null;
  const falsa = pregunta?.opciones.find((o) => !o.verdadera);

  function empezar() {
    const nueva = armarPartida(preguntas);
    if (!nueva) return;
    setNombres([nombres[0].trim() || "Jugador 1", nombres[1].trim() || "Jugador 2"]);
    setPartida(nueva);
    setActual(0);
    setElegida(null);
    setPuntos([0, 0]);
  }

  function responder(qid: string) {
    if (!pregunta || respondida) return;
    setElegida(qid);
    if (qid === falsa?.qid) {
      const p: [number, number] = [...puntos];
      p[turno] += 1;
      setPuntos(p);
    }
  }

  function siguiente() {
    setElegida(null);
    setActual(actual + 1);
  }

  // Teclado (laptop): 1-5 para responder, Enter o espacio para seguir.
  useEffect(() => {
    if (!pregunta) return;
    function alTeclear(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.metaKey || e.ctrlKey || e.altKey) return;
      if (!respondida) {
        const n = Number(e.key);
        if (n >= 1 && n <= pregunta!.opciones.length) responder(pregunta!.opciones[n - 1].qid);
      } else if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        siguiente();
      }
    }
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  });

  // ---------------------------------------------------------------- Nombres
  if (!partida) {
    return (
      <form
        className="mt-6 flex flex-col gap-4 lg:mt-10 lg:gap-6"
        onSubmit={(e) => {
          e.preventDefault();
          empezar();
        }}
      >
        <div className="rounded-2xl bg-superficie-2 p-4 text-sm lg:p-6 lg:text-base">
          <p className="font-display text-lg font-bold uppercase lg:text-2xl">Cómo se juega</p>
          <p className="mt-1 text-tenue">
            Dos jugadores, una pantalla. Se turnan: cada uno responde {RONDAS} preguntas ({PLAN[0].rondas} fáciles,{" "}
            {PLAN[1].rondas} intermedias y {PLAN[2].rondas} difíciles). Cada acierto vale 1 punto. Gana quien
            sume más.
          </p>
          <p className="mt-2 hidden text-tenue lg:block">
            En la laptop puedes responder con las teclas <Tecla>1</Tecla> a <Tecla>5</Tecla> y pasar al siguiente
            turno con <Tecla>Enter</Tecla>.
          </p>
        </div>
        <div className="flex flex-col gap-4 lg:grid lg:grid-cols-2 lg:gap-6">
          {[0, 1].map((i) => (
            <label key={i} className="flex flex-col gap-1.5">
              <span className={`font-display text-base font-bold uppercase lg:text-lg ${COLOR[i].texto}`}>
                Jugador {i + 1}
              </span>
              <input
                value={nombres[i]}
                onChange={(e) => {
                  const n: [string, string] = [...nombres];
                  n[i] = e.target.value.slice(0, 20);
                  setNombres(n);
                }}
                placeholder={i === 0 ? "Tu nombre" : "Nombre de tu amigo"}
                autoComplete="off"
                autoFocus={i === 0}
                className={`rounded-2xl border-2 bg-superficie px-4 py-3 text-lg font-semibold outline-none placeholder:font-normal placeholder:text-tenue lg:px-5 lg:py-4 lg:text-xl ${COLOR[i].foco} border-borde`}
              />
            </label>
          ))}
        </div>
        {faltan.length > 0 ? (
          <p className="text-center text-sm text-roja">
            Todavía no hay suficientes preguntas ({faltan.join(", ")}) para una partida completa.
          </p>
        ) : (
          <button
            type="submit"
            className="mt-1 rounded-full bg-cancha px-6 py-3 font-display text-xl font-bold uppercase tracking-wide text-sobre-cancha hover:bg-cancha-fuerte active:scale-[0.99] lg:self-center lg:px-16 lg:py-4 lg:text-2xl"
          >
            ¡A jugar!
          </button>
        )}
      </form>
    );
  }

  // ---------------------------------------------------------------- Final
  if (!pregunta) {
    const ganador = puntos[0] === puntos[1] ? null : puntos[0] > puntos[1] ? 0 : 1;
    return (
      <section className="aparecer mt-6 flex flex-col items-center gap-4 rounded-3xl border border-borde bg-superficie p-6 text-center shadow-sm lg:mx-auto lg:mt-10 lg:w-full lg:max-w-2xl lg:gap-6 lg:p-12">
        <p className="font-display text-lg font-bold uppercase text-tenue lg:text-2xl">Final del partido</p>
        <p className="font-display text-4xl leading-none font-extrabold uppercase lg:text-7xl">
          {ganador === null ? (
            "¡Empate!"
          ) : (
            <>
              ¡Ganó <span className={COLOR[ganador].texto}>{nombres[ganador]}</span>!
            </>
          )}
        </p>
        <Marcador nombres={nombres} puntos={puntos} turno={ganador ?? -1} grande />
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
            onClick={() => setPartida(null)}
            className="rounded-full border border-borde bg-superficie px-5 py-2.5 font-display text-lg font-bold uppercase tracking-wide hover:bg-superficie-2 lg:px-8 lg:py-3 lg:text-xl"
          >
            Cambiar jugadores
          </button>
        </div>
      </section>
    );
  }

  // ---------------------------------------------------------------- Pregunta
  const ronda = Math.floor(actual / 2) + 1;
  const acerto = respondida && elegida === falsa?.qid;
  const ultima = actual + 1 >= partida.length;

  return (
    <section className="mt-5 flex flex-col gap-3 lg:mt-8 lg:grid lg:grid-cols-[17rem_1fr] lg:items-start lg:gap-10">
      {/* Panel lateral en laptop; arriba en celular */}
      <aside className="flex flex-col gap-3 lg:sticky lg:top-6 lg:gap-4 lg:rounded-3xl lg:border lg:border-borde lg:bg-superficie lg:p-5 lg:shadow-sm">
        <Marcador nombres={nombres} puntos={puntos} turno={turno} lateral />
        <div className="flex items-center justify-between text-sm text-tenue">
          <span>
            Ronda {ronda} de {RONDAS}
          </span>
          <span className="rounded-full bg-superficie-2 px-2.5 py-0.5 font-medium">
            {NOMBRE_DIFICULTAD[pregunta.dificultad]}
          </span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-superficie-2">
          <div
            className="h-full rounded-full bg-cancha transition-all"
            style={{ width: `${(actual / partida.length) * 100}%` }}
          />
        </div>
        <p className="hidden text-xs leading-relaxed text-tenue lg:block">
          Responde con <Tecla>1</Tecla>–<Tecla>5</Tecla>. Sigue con <Tecla>Enter</Tecla>.
        </p>
      </aside>

      <div className="flex flex-col gap-3 lg:gap-4">
        <div key={pregunta.id} className="aparecer flex flex-col gap-1">
          <p className={`font-display text-lg font-extrabold uppercase lg:text-2xl ${COLOR[turno].texto}`}>
            Turno de {nombres[turno]}
          </p>
          <h2 className="font-display text-2xl leading-tight font-extrabold uppercase lg:text-5xl lg:leading-[1.05]">
            {pregunta.afirmacion}
          </h2>
          <p className="text-sm text-tenue lg:text-base">¿Cuál es el dato falso?</p>
        </div>

        <div className="flex flex-col gap-2 lg:gap-2.5">
          {pregunta.opciones.map((o, i) => {
            const esLaFalsa = !o.verdadera;
            const laElegi = elegida === o.qid;
            let estilo = "border border-borde bg-superficie hover:bg-superficie-2";
            if (respondida && esLaFalsa) estilo = "bg-roja text-white";
            else if (respondida && laElegi) estilo = "border-2 border-tinta bg-superficie";
            else if (respondida) estilo = "border border-borde bg-superficie opacity-60";
            return (
              <button
                key={o.qid}
                type="button"
                onClick={() => responder(o.qid)}
                disabled={respondida}
                className={`flex min-h-14 items-center justify-between gap-3 rounded-2xl px-4 py-3 text-left font-semibold shadow-sm transition active:scale-[0.99] lg:min-h-16 lg:px-5 lg:text-lg ${estilo}`}
              >
                <span className="flex items-center gap-4">
                  <span
                    className={`hidden h-8 w-8 shrink-0 items-center justify-center rounded-lg font-display text-lg font-bold lg:inline-flex ${
                      respondida && esLaFalsa ? "bg-white/20" : "bg-superficie-2 text-tenue"
                    }`}
                    aria-hidden="true"
                  >
                    {i + 1}
                  </span>
                  {o.texto}
                </span>
                {respondida && esLaFalsa && (
                  <span className="shrink-0 rounded-full bg-white/20 px-2 py-0.5 font-display text-sm font-bold uppercase lg:text-base">
                    Falso
                  </span>
                )}
                {respondida && !esLaFalsa && (
                  <span className="shrink-0 text-cancha lg:text-xl" aria-label="verdadero">✓</span>
                )}
              </button>
            );
          })}
        </div>

        {respondida && (
          <div className="aparecer flex flex-col gap-3 rounded-2xl bg-superficie-2 p-4 lg:flex-row lg:items-center lg:gap-6 lg:p-5" aria-live="polite">
            <div className="flex flex-col gap-1 lg:flex-1">
              <p className={`font-display text-xl font-extrabold uppercase lg:text-2xl ${acerto ? COLOR[turno].texto : "text-roja"}`}>
                {acerto ? `¡Punto para ${nombres[turno]}!` : `¡Engañaron a ${nombres[turno]}!`}
              </p>
              <p className="text-sm lg:text-base">{pregunta.explicacion}</p>
            </div>
            <button
              type="button"
              onClick={siguiente}
              autoFocus
              className="self-end rounded-full bg-cancha px-5 py-2.5 font-display text-base font-bold uppercase tracking-wide whitespace-nowrap text-sobre-cancha hover:bg-cancha-fuerte lg:self-center lg:px-7 lg:py-3 lg:text-lg"
            >
              {ultima ? "Ver resultado" : `Turno de ${nombres[1 - turno]} →`}
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

function Tecla({ children }: { children: ReactNode }) {
  return (
    <kbd className="rounded-md border border-borde bg-superficie px-1.5 py-0.5 font-sans text-xs font-semibold text-tinta">
      {children}
    </kbd>
  );
}

function Marcador({
  nombres,
  puntos,
  turno,
  grande = false,
  lateral = false,
}: {
  nombres: [string, string];
  puntos: [number, number];
  turno: number;
  grande?: boolean;
  lateral?: boolean;
}) {
  return (
    <div className={`grid w-full grid-cols-2 gap-2 ${lateral ? "lg:grid-cols-1" : "lg:gap-4"}`}>
      {[0, 1].map((i) => {
        const activo = turno === i;
        return (
          <div
            key={i}
            className={`flex items-center justify-between gap-2 rounded-2xl px-4 py-2.5 transition ${
              grande ? "lg:px-6 lg:py-4" : "lg:py-3"
            } ${activo ? `${COLOR[i].fondo} ${COLOR[i].sobre} shadow-md` : "border border-borde bg-superficie"}`}
          >
            <span className={`truncate font-semibold ${grande ? "lg:text-xl" : "lg:text-lg"}`}>{nombres[i]}</span>
            <span
              className={`font-display font-extrabold leading-none ${grande ? "text-4xl lg:text-6xl" : "text-3xl lg:text-4xl"}`}
            >
              {puntos[i]}
            </span>
          </div>
        );
      })}
    </div>
  );
}
