"use client";

import { useEffect, useRef, useState } from "react";
import { Avatar, CreditosFotos } from "../../componentes/Foto";
import type { Categoria, Resultado } from "./tipos";

const RONDAS = 15;

const COLOR = [
  { fondo: "bg-cancha", texto: "text-cancha", foco: "focus:border-cancha", sobre: "text-sobre-cancha", borde: "border-cancha" },
  { fondo: "bg-rival", texto: "text-rival", foco: "focus:border-rival", sobre: "text-sobre-rival", borde: "border-rival" },
];

const NOMBRE_DIFICULTAD = { facil: "Fácil", intermedio: "Intermedia", dificil: "Difícil" } as const;

type Sugerencia = { qid: string; nombre: string; popularidad: number };
type Verificado = { qid: string; nombre: string; cumple: boolean | null };

/** 15 categorías al azar, con más fáciles e intermedias que difíciles. */
function elegirRondas(categorias: Categoria[]): Categoria[] {
  const peso = { facil: 3, intermedio: 2, dificil: 1 };
  const conPeso = categorias.map((c) => ({ c, k: Math.random() ** (1 / peso[c.dificultad]) }));
  return conPeso
    .sort((a, b) => b.k - a.k)
    .slice(0, RONDAS)
    .map((x) => x.c);
}

export default function UltimoEnPie({ categorias }: { categorias: Categoria[] }) {
  const [nombres, setNombres] = useState<[string, string]>(["", ""]);
  const [rondas, setRondas] = useState<Categoria[] | null>(null);
  const [actual, setActual] = useState(0);
  const [puntos, setPuntos] = useState<[number, number]>([0, 0]);
  const [ganadorRonda, setGanadorRonda] = useState<0 | 1 | null>(null);
  const [verificados, setVerificados] = useState<Verificado[]>([]);

  function empezar() {
    setNombres([nombres[0].trim() || "Jugador 1", nombres[1].trim() || "Jugador 2"]);
    setRondas(elegirRondas(categorias));
    setActual(0);
    setPuntos([0, 0]);
    setGanadorRonda(null);
    setVerificados([]);
  }

  function darPunto(i: 0 | 1) {
    if (ganadorRonda !== null) return;
    const p: [number, number] = [...puntos];
    p[i] += 1;
    setPuntos(p);
    setGanadorRonda(i);
  }

  function deshacer() {
    if (ganadorRonda === null) return;
    const p: [number, number] = [...puntos];
    p[ganadorRonda] -= 1;
    setPuntos(p);
    setGanadorRonda(null);
  }

  function siguiente() {
    setGanadorRonda(null);
    setVerificados([]);
    setActual(actual + 1);
  }

  // ---------------------------------------------------------------- Nombres
  if (!rondas) {
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
            <li>Aparece una categoría, por ejemplo «Jugaron en Barcelona y en Real Madrid».</li>
            <li>Por turnos, digan en voz alta un jugador que la cumpla. No se vale repetir.</li>
            <li>
              Si desconfías de lo que dijo tu rival, búscalo en el <strong className="text-tinta">verificador</strong>.
              Si no cumple, ganas la ronda. Si cumple y desconfiaste, la pierdes.
            </li>
            <li>El que se queda sin nombres pierde la ronda. Marquen al ganador con la flecha ▲ de su nombre.</li>
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
  if (actual >= rondas.length) {
    const ganador = puntos[0] === puntos[1] ? null : puntos[0] > puntos[1] ? 0 : 1;
    return (
      <section className="aparecer mt-6 flex flex-col items-center gap-4 rounded-3xl border border-borde bg-superficie p-6 text-center shadow-sm lg:mx-auto lg:mt-10 lg:w-full lg:max-w-2xl lg:gap-6 lg:p-12">
        <p className="font-display text-lg font-bold uppercase text-tenue lg:text-2xl">Final del partido</p>
        <p className="font-display text-4xl leading-none font-extrabold uppercase lg:text-7xl">
          {ganador === null ? (
            "¡Empate!"
          ) : (
            <>
              <span className={COLOR[ganador].texto}>{nombres[ganador]}</span> quedó en pie
            </>
          )}
        </p>
        <Marcador nombres={nombres} puntos={puntos} resaltado={ganador ?? -1} />
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
            onClick={() => setRondas(null)}
            className="rounded-full border border-borde bg-superficie px-5 py-2.5 font-display text-lg font-bold uppercase tracking-wide hover:bg-superficie-2 lg:px-8 lg:py-3 lg:text-xl"
          >
            Cambiar jugadores
          </button>
        </div>
      </section>
    );
  }

  // ---------------------------------------------------------------- Ronda
  const categoria = rondas[actual];
  const empieza = actual % 2;

  return (
    <section className="mt-5 flex flex-col gap-4 lg:mt-8 lg:grid lg:grid-cols-[1fr_20rem] lg:items-start lg:gap-10">
      <div className="flex flex-col gap-4 lg:gap-5">
        <div className="flex items-center justify-between text-sm text-tenue">
          <span>
            Ronda {actual + 1} de {rondas.length}
          </span>
          <span className="rounded-full bg-superficie-2 px-2.5 py-0.5 font-medium">
            Categoría {NOMBRE_DIFICULTAD[categoria.dificultad]}
          </span>
        </div>

        {/* Categoría */}
        <div
          key={categoria.id}
          className="aparecer grano relative overflow-hidden rounded-3xl bg-noche p-6 text-white shadow-lg lg:p-10"
        >
          <div className="reflectores absolute inset-0" aria-hidden="true" />
          <p className="relative font-display text-sm font-bold uppercase tracking-[0.2em] text-tarjeta lg:text-base">
            La categoría es
          </p>
          <h2 className="relative mt-2 font-display text-3xl leading-[1.05] font-extrabold uppercase lg:text-6xl">
            {categoria.titulo}
          </h2>
          <p className="relative mt-4 text-sm text-white/75 lg:text-base">
            Empieza{" "}
            <span className={`rounded-full px-2.5 py-0.5 font-semibold ${COLOR[empieza].fondo} ${COLOR[empieza].sobre}`}>
              {nombres[empieza]}
            </span>
          </p>
        </div>

        {ganadorRonda === null ? (
          <>
            <Buscador
              key={categoria.id}
              categoriaId={categoria.id}
              onVerificado={(v) => setVerificados((lista) => [v, ...lista.filter((x) => x.qid !== v.qid)])}
            />
            {verificados.length > 0 && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-tenue">Verificados en esta ronda</p>
                <ul className="mt-2 flex flex-wrap gap-1.5">
                  {verificados.map((v) => (
                    <li
                      key={v.qid}
                      className={`rounded-full px-3 py-1 text-sm font-medium ${
                        v.cumple === true
                          ? "bg-cancha/10 text-cancha"
                          : v.cumple === false
                            ? "bg-roja/10 text-roja"
                            : "bg-superficie-2 text-tenue"
                      }`}
                    >
                      {v.cumple === true ? "✓" : v.cumple === false ? "✗" : "?"} {v.nombre}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        ) : (
          <div className="aparecer flex flex-col gap-4 rounded-3xl bg-superficie-2 p-5 lg:p-7" aria-live="polite">
            <p className={`font-display text-2xl font-extrabold uppercase lg:text-3xl ${COLOR[ganadorRonda].texto}`}>
              ¡Ronda para {nombres[ganadorRonda]}!
            </p>
            <div>
              <p className="text-sm font-semibold text-tenue">
                Algunos que valían ({categoria.cantidad} jugadores conocidos cumplen esta categoría):
              </p>
              <ul className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
                {categoria.miembros_destacados.map((m) => (
                  <li key={m.nombre} className="flex items-center gap-2 rounded-2xl border border-borde bg-superficie p-2 text-sm">
                    <Avatar nombre={m.nombre} foto={m.foto} tamano={36} />
                    <span className="leading-tight font-medium">{m.nombre}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-2">
                <CreditosFotos fotos={categoria.miembros_destacados} />
              </div>
            </div>
            <div className="flex flex-wrap justify-end gap-2">
              <button
                type="button"
                onClick={deshacer}
                className="rounded-full border border-borde bg-superficie px-5 py-2.5 font-display text-base font-bold uppercase tracking-wide hover:bg-superficie"
              >
                Deshacer
              </button>
              <button
                type="button"
                onClick={siguiente}
                autoFocus
                className="rounded-full bg-cancha px-6 py-2.5 font-display text-base font-bold uppercase tracking-wide text-sobre-cancha hover:bg-cancha-fuerte lg:text-lg"
              >
                {actual + 1 < rondas.length ? "Siguiente ronda →" : "Ver resultado"}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Marcador con flechas */}
      <aside className="flex flex-col gap-3 lg:sticky lg:top-24 lg:rounded-3xl lg:border lg:border-borde lg:bg-superficie lg:p-5 lg:shadow-sm">
        <p className="font-display text-lg font-bold uppercase">Marcador</p>
        <Marcador
          nombres={nombres}
          puntos={puntos}
          resaltado={ganadorRonda ?? -1}
          onPunto={ganadorRonda === null ? darPunto : undefined}
        />
        <p className="text-xs text-tenue">
          {ganadorRonda === null
            ? "Cuando termine la ronda, toca la flecha ▲ de quien ganó."
            : "Punto guardado. Si te equivocaste, usa «Deshacer»."}
        </p>
        <div className="h-1.5 overflow-hidden rounded-full bg-superficie-2">
          <div
            className="h-full rounded-full bg-cancha transition-all"
            style={{ width: `${(actual / rondas.length) * 100}%` }}
          />
        </div>
      </aside>
    </section>
  );
}

// ------------------------------------------------------------------ Buscador

function Buscador({
  categoriaId,
  onVerificado,
}: {
  categoriaId: number;
  onVerificado: (v: Verificado) => void;
}) {
  const [texto, setTexto] = useState("");
  const [sugerencias, setSugerencias] = useState<Sugerencia[]>([]);
  const [activa, setActiva] = useState(0);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [estado, setEstado] = useState<"listo" | "verificando" | "error">("listo");
  const entrada = useRef<HTMLInputElement>(null);

  // Sugerencias mientras se escribe (espera 250 ms entre teclas)
  useEffect(() => {
    if (texto.trim().length < 2) return;
    const control = new AbortController();
    const espera = setTimeout(() => {
      fetch(`/api/jugadores?q=${encodeURIComponent(texto)}`, { signal: control.signal })
        .then((r) => r.json())
        .then((filas) => {
          setSugerencias(Array.isArray(filas) ? filas : []);
          setActiva(0);
        })
        .catch(() => {});
    }, 250);
    return () => {
      clearTimeout(espera);
      control.abort();
    };
  }, [texto]);

  // "/" enfoca el buscador (laptop)
  useEffect(() => {
    function alTeclear(e: KeyboardEvent) {
      if (e.key === "/" && document.activeElement !== entrada.current) {
        e.preventDefault();
        entrada.current?.focus();
      }
    }
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, []);

  async function verificar(s: Sugerencia) {
    setTexto("");
    setSugerencias([]);
    setEstado("verificando");
    try {
      const r = await fetch(`/api/ultimo-en-pie/verificar?categoria=${categoriaId}&jugador=${s.qid}`);
      if (!r.ok) throw new Error();
      const datos: Resultado = await r.json();
      setResultado(datos);
      setEstado("listo");
      onVerificado({ qid: s.qid, nombre: datos.nombre, cumple: datos.cumple });
    } catch {
      setEstado("error");
    }
  }

  const abiertas = texto.trim().length >= 2 && sugerencias.length > 0;

  return (
    <div className="flex flex-col gap-3">
      <div className="relative">
        <label htmlFor="buscador" className="text-xs font-semibold uppercase tracking-wide text-tenue">
          ¿Desconfías? Verifica a un jugador
        </label>
        <div className="mt-1.5 flex items-center gap-2 rounded-2xl border-2 border-borde bg-superficie px-4 focus-within:border-tinta">
          <svg viewBox="0 0 24 24" className="h-5 w-5 shrink-0 text-tenue" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="M20 20l-3.5-3.5" />
          </svg>
          <input
            id="buscador"
            ref={entrada}
            value={texto}
            onChange={(e) => {
              setTexto(e.target.value);
              if (e.target.value.trim().length < 2) setSugerencias([]);
            }}
            onKeyDown={(e) => {
              if (!abiertas) return;
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setActiva((a) => Math.min(a + 1, sugerencias.length - 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setActiva((a) => Math.max(a - 1, 0));
              } else if (e.key === "Enter") {
                e.preventDefault();
                verificar(sugerencias[activa]);
              }
            }}
            placeholder="Escribe un nombre, por ejemplo «Neymar»"
            autoComplete="off"
            role="combobox"
            aria-expanded={abiertas}
            aria-controls="sugerencias"
            className="w-full bg-transparent py-3 text-lg outline-none placeholder:text-tenue lg:py-4"
          />
          <kbd className="hidden rounded-md border border-borde px-1.5 py-0.5 text-xs text-tenue lg:inline">/</kbd>
        </div>
        {abiertas && (
          <ul
            id="sugerencias"
            role="listbox"
            className="absolute inset-x-0 top-full z-20 mt-1.5 overflow-hidden rounded-2xl border border-borde bg-superficie shadow-xl"
          >
            {sugerencias.map((s, i) => (
              <li key={s.qid} role="option" aria-selected={i === activa}>
                <button
                  type="button"
                  onMouseEnter={() => setActiva(i)}
                  onClick={() => verificar(s)}
                  className={`flex w-full items-center justify-between px-4 py-2.5 text-left ${
                    i === activa ? "bg-superficie-2" : ""
                  }`}
                >
                  <span className="font-semibold">{s.nombre}</span>
                  <span className="text-xs text-tenue">Verificar ↵</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {estado === "verificando" && <p className="text-sm text-tenue">Verificando…</p>}
      {estado === "error" && <p className="text-sm text-roja">No se pudo verificar ahora. Inténtalo de nuevo.</p>}

      {resultado && estado === "listo" && (
        <div
          className={`aparecer rounded-2xl border-2 p-4 lg:p-5 ${
            resultado.cumple === true
              ? "border-cancha bg-cancha/5"
              : resultado.cumple === false
                ? "border-roja bg-roja/5"
                : "border-borde bg-superficie-2"
          }`}
          aria-live="polite"
        >
          <div className="flex items-center gap-4">
            <Avatar nombre={resultado.nombre} foto={resultado.foto} tamano={64} />
            <div>
              <p className="flex flex-wrap items-center gap-x-2 font-display text-2xl font-extrabold uppercase lg:text-3xl">
                <span
                  className={
                    resultado.cumple === true ? "text-cancha" : resultado.cumple === false ? "text-roja" : "text-tenue"
                  }
                >
                  {resultado.cumple === true ? "✓ Cumple" : resultado.cumple === false ? "✗ No cumple" : "? Sin datos"}
                </span>
                <span className="text-tinta">· {resultado.nombre}</span>
              </p>
              <p className="mt-1 text-sm text-tenue">{resultado.detalle}</p>
            </div>
          </div>
          {resultado.evidencia.length > 0 && (
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {resultado.evidencia.map((e, i) => (
                <li
                  key={`${e.texto}-${i}`}
                  className={`rounded-lg px-2.5 py-1 text-sm ${
                    e.destacado ? "bg-cancha font-semibold text-sobre-cancha" : "border border-borde bg-superficie"
                  }`}
                >
                  {e.texto}
                  {e.detalle && <span className="ml-1.5 text-xs opacity-75">{e.detalle}</span>}
                </li>
              ))}
            </ul>
          )}
          <div className="mt-2">
            <CreditosFotos fotos={[{ nombre: resultado.nombre, foto: resultado.foto }]} />
          </div>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ Marcador

function Marcador({
  nombres,
  puntos,
  resaltado,
  onPunto,
}: {
  nombres: [string, string];
  puntos: [number, number];
  resaltado: number;
  onPunto?: (i: 0 | 1) => void;
}) {
  return (
    <div className="grid w-full grid-cols-2 gap-2 lg:grid-cols-1">
      {([0, 1] as const).map((i) => (
        <div
          key={i}
          className={`flex items-center gap-2 rounded-2xl px-3 py-2.5 transition lg:py-3 ${
            resaltado === i ? `${COLOR[i].fondo} ${COLOR[i].sobre} shadow-md` : `border-2 ${COLOR[i].borde} bg-superficie`
          }`}
        >
          {onPunto && (
            <button
              type="button"
              onClick={() => onPunto(i)}
              aria-label={`Ronda para ${nombres[i]}`}
              title={`Ronda para ${nombres[i]}`}
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-lg font-bold transition hover:-translate-y-0.5 active:scale-95 ${COLOR[i].fondo} ${COLOR[i].sobre}`}
            >
              ▲
            </button>
          )}
          <span className="min-w-0 flex-1 truncate font-semibold lg:text-lg">{nombres[i]}</span>
          <span className="font-display text-3xl leading-none font-extrabold lg:text-4xl">{puntos[i]}</span>
        </div>
      ))}
    </div>
  );
}
