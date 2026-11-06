"use client";

import { useState } from "react";
import { Avatar, CreditosFotos } from "../../componentes/Foto";
import type { Dificultad, Ronda } from "./tipos";

/** 15 rondas: 5 fáciles, 5 intermedias y 5 difíciles, en ese orden. */
const PLAN: { dificultad: Dificultad; rondas: number }[] = [
  { dificultad: "facil", rondas: 5 },
  { dificultad: "intermedio", rondas: 5 },
  { dificultad: "dificil", rondas: 5 },
];
const TOTAL = PLAN.reduce((t, p) => t + p.rondas, 0);
const CUMPLEN = 12;

const NOMBRE_DIFICULTAD: Record<Dificultad, string> = { facil: "Fácil", intermedio: "Intermedia", dificil: "Difícil" };

const COLOR = [
  { fondo: "bg-cancha", texto: "text-cancha", foco: "focus:border-cancha", sobre: "text-sobre-cancha", borde: "border-cancha" },
  { fondo: "bg-rival", texto: "text-rival", foco: "focus:border-rival", sobre: "text-sobre-rival", borde: "border-rival" },
];

function mezclar<T>(lista: T[]): T[] {
  const copia = [...lista];
  for (let i = copia.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copia[i], copia[j]] = [copia[j], copia[i]];
  }
  return copia;
}

/** Elige las rondas sin repetir categoría (cada categoría tiene varias versiones). */
function armarPartida(rondas: Ronda[]): Ronda[] | null {
  const usadas = new Set<string>();
  const partida: Ronda[] = [];
  for (const { dificultad, rondas: n } of PLAN) {
    const elegidas: Ronda[] = [];
    for (const r of mezclar(rondas.filter((x) => x.dificultad === dificultad))) {
      if (elegidas.length === n) break;
      if (usadas.has(r.categoria)) continue;
      usadas.add(r.categoria);
      elegidas.push(r);
    }
    if (elegidas.length < n) return null;
    partida.push(...elegidas.map((r) => ({ ...r, fichas: mezclar(r.fichas) })));
  }
  return partida;
}

export default function Buscaminas({ rondas }: { rondas: Ronda[] }) {
  const [nombres, setNombres] = useState<[string, string]>(["", ""]);
  const [partida, setPartida] = useState<Ronda[] | null>(null);
  const [actual, setActual] = useState(0);
  const [puntos, setPuntos] = useState<[number, number]>([0, 0]);
  const [reveladas, setReveladas] = useState<string[]>([]);
  const [turno, setTurno] = useState<0 | 1>(0);
  const [caida, setCaida] = useState<{ qid: string; jugador: 0 | 1 } | null>(null);
  const [error, setError] = useState(false);

  function empezar() {
    const nueva = armarPartida(rondas);
    if (!nueva) {
      setError(true);
      return;
    }
    setError(false);
    setNombres([nombres[0].trim() || "Jugador 1", nombres[1].trim() || "Jugador 2"]);
    setPartida(nueva);
    setActual(0);
    setPuntos([0, 0]);
    setReveladas([]);
    setTurno(0);
    setCaida(null);
  }

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
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-tenue">
            <li>Aparece una categoría y 16 jugadores: 12 la cumplen y 4 son impostores 💣.</li>
            <li>Por turnos, toquen a un jugador que crean que cumple.</li>
            <li>
              Si tocas un impostor, <strong className="text-tinta">pierdes la ronda</strong> y tu rival suma un punto.
            </li>
            <li>Si se descubren los 12 sin que nadie caiga, la ronda queda empatada.</li>
            <li>
              {TOTAL} rondas: {PLAN[0].rondas} fáciles, {PLAN[1].rondas} intermedias y {PLAN[2].rondas} difíciles.
            </li>
          </ol>
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
                className={`rounded-2xl border-2 border-borde bg-superficie px-4 py-3 text-lg font-semibold outline-none placeholder:font-normal placeholder:text-tenue lg:px-5 lg:py-4 lg:text-xl ${COLOR[i].foco}`}
              />
            </label>
          ))}
        </div>
        {error && (
          <p className="text-center text-sm text-roja">Todavía no hay suficientes rondas para una partida completa.</p>
        )}
        <button
          type="submit"
          className="mt-1 rounded-full bg-cancha px-6 py-3 font-display text-xl font-bold uppercase tracking-wide text-sobre-cancha hover:bg-cancha-fuerte active:scale-[0.99] lg:self-center lg:px-16 lg:py-4 lg:text-2xl"
        >
          ¡A jugar!
        </button>
      </form>
    );
  }

  // ---------------------------------------------------------------- Final
  if (actual >= partida.length) {
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
        <Marcador nombres={nombres} puntos={puntos} activo={ganador ?? -1} />
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

  // ---------------------------------------------------------------- Ronda
  const ronda = partida[actual];
  const aciertos = reveladas.filter((q) => ronda.fichas.find((f) => f.qid === q)?.cumple).length;
  const empate = !caida && aciertos >= CUMPLEN;
  const terminada = Boolean(caida) || empate;

  function tocar(qid: string) {
    if (terminada || reveladas.includes(qid)) return;
    const ficha = ronda.fichas.find((f) => f.qid === qid)!;
    setReveladas([...reveladas, qid]);
    if (!ficha.cumple) {
      // Cayó en un impostor: pierde la ronda y suma el rival
      setCaida({ qid, jugador: turno });
      const p: [number, number] = [...puntos];
      p[1 - turno] += 1;
      setPuntos(p);
      return;
    }
    setTurno(turno === 0 ? 1 : 0);
  }

  function siguiente() {
    const proxima = actual + 1;
    setActual(proxima);
    setReveladas([]);
    setCaida(null);
    setTurno((proxima % 2) as 0 | 1); // empieza un jugador distinto cada ronda
  }

  return (
    <section className="mt-5 flex flex-col gap-4 lg:mt-8 lg:grid lg:grid-cols-[1fr_18rem] lg:items-start lg:gap-10">
      <div className="flex flex-col gap-4">
        <div key={ronda.id} className="aparecer grano relative overflow-hidden rounded-3xl bg-noche p-5 text-white shadow-lg lg:p-7">
          <div className="reflectores absolute inset-0" aria-hidden="true" />
          <p className="relative font-display text-sm font-bold uppercase tracking-[0.2em] text-tarjeta">
            Ronda {actual + 1} de {partida.length} · {NOMBRE_DIFICULTAD[ronda.dificultad]}
          </p>
          <h2 className="relative mt-1.5 font-display text-2xl leading-[1.05] font-extrabold uppercase lg:text-4xl">
            {ronda.titulo}
          </h2>
          <p className="relative mt-2 text-sm text-white/70">12 cumplen y 4 son impostores 💣</p>
        </div>

        <div className="grid grid-cols-4 gap-2 lg:gap-3">
          {ronda.fichas.map((f) => {
            const visible = reveladas.includes(f.qid) || (terminada && !f.cumple);
            const esLaCaida = caida?.qid === f.qid;
            let estilo = "border border-borde bg-superficie hover:-translate-y-0.5 hover:border-tinta/30 hover:shadow-md";
            if (visible && f.cumple) estilo = "border-2 border-cancha bg-cancha/10";
            if (visible && !f.cumple) estilo = esLaCaida ? "bg-roja text-white ring-4 ring-roja/30" : "border-2 border-roja bg-roja/10";
            if (terminada && !visible) estilo = "border border-borde bg-superficie opacity-60";
            return (
              <button
                key={f.qid}
                type="button"
                onClick={() => tocar(f.qid)}
                disabled={terminada || visible}
                className={`relative flex h-28 flex-col items-center justify-center gap-1.5 rounded-2xl px-1 text-center font-display text-[11px] leading-[1.05] font-bold uppercase shadow-sm transition sm:h-32 sm:text-xs lg:h-44 lg:gap-2 lg:rounded-3xl lg:text-sm ${estilo}`}
              >
                <Avatar nombre={f.nombre} foto={f.foto} tamano={52} className="lg:hidden" />
                <Avatar nombre={f.nombre} foto={f.foto} tamano={92} className="hidden lg:inline-flex" />
                <span className="line-clamp-2">{f.nombre}</span>
                {visible && (
                  <span
                    className={`absolute top-1.5 right-1.5 flex h-6 w-6 items-center justify-center rounded-full text-sm lg:h-8 lg:w-8 lg:text-base ${
                      f.cumple ? "bg-cancha text-sobre-cancha" : "bg-white text-roja"
                    }`}
                    aria-label={f.cumple ? "cumple" : "impostor"}
                  >
                    {f.cumple ? "✓" : "💣"}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {terminada && (
          <div className="aparecer flex flex-col gap-3 rounded-2xl bg-superficie-2 p-4 lg:flex-row lg:items-center lg:gap-6 lg:p-5" aria-live="polite">
            <div className="flex flex-col gap-1 lg:flex-1">
              <p
                className={`font-display text-xl font-extrabold uppercase lg:text-2xl ${
                  caida ? COLOR[1 - caida.jugador].texto : "text-tinta"
                }`}
              >
                {caida
                  ? `💣 ${nombres[caida.jugador]} tocó un impostor: punto para ${nombres[1 - caida.jugador]}`
                  : "¡Nadie cayó! Ronda empatada"}
              </p>
              <p className="text-sm lg:text-base">{ronda.explicacion}</p>
              <CreditosFotos fotos={ronda.fichas} />
            </div>
            <button
              type="button"
              onClick={siguiente}
              autoFocus
              className="self-end rounded-full bg-cancha px-6 py-2.5 font-display text-base font-bold uppercase tracking-wide whitespace-nowrap text-sobre-cancha hover:bg-cancha-fuerte lg:self-center lg:py-3 lg:text-lg"
            >
              {actual + 1 < partida.length ? "Siguiente ronda →" : "Ver resultado"}
            </button>
          </div>
        )}
      </div>

      <aside className="flex flex-col gap-3 lg:sticky lg:top-24 lg:rounded-3xl lg:border lg:border-borde lg:bg-superficie lg:p-5 lg:shadow-sm">
        <p className="font-display text-lg font-bold uppercase">Marcador</p>
        <Marcador nombres={nombres} puntos={puntos} activo={terminada ? -1 : turno} />
        {!terminada && (
          <p className={`font-display text-lg font-extrabold uppercase ${COLOR[turno].texto}`}>Turno de {nombres[turno]}</p>
        )}
        <p className="text-sm text-tenue">
          Descubiertos: <strong className="text-tinta">{aciertos}</strong> de {CUMPLEN}
        </p>
        <div className="h-1.5 overflow-hidden rounded-full bg-superficie-2">
          <div className="h-full rounded-full bg-cancha transition-all" style={{ width: `${(actual / partida.length) * 100}%` }} />
        </div>
      </aside>
    </section>
  );
}

function Marcador({ nombres, puntos, activo }: { nombres: [string, string]; puntos: [number, number]; activo: number }) {
  return (
    <div className="grid w-full grid-cols-2 gap-2 lg:grid-cols-1">
      {([0, 1] as const).map((i) => (
        <div
          key={i}
          className={`flex items-center justify-between gap-2 rounded-2xl px-4 py-2.5 transition lg:py-3 ${
            activo === i ? `${COLOR[i].fondo} ${COLOR[i].sobre} shadow-md` : `border-2 ${COLOR[i].borde} bg-superficie`
          }`}
        >
          <span className="truncate font-semibold lg:text-lg">{nombres[i]}</span>
          <span className="font-display text-3xl leading-none font-extrabold lg:text-4xl">{puntos[i]}</span>
        </div>
      ))}
    </div>
  );
}
