import Link from "next/link";
import type { ReactNode } from "react";
import { leerEstadisticas } from "@/lib/estadisticas";
import { Cancha } from "./componentes/Cancha";

type Juego = {
  numero: string;
  titulo: string;
  descripcion: string;
  etiquetas: string[];
  href?: string;
  fondo: string;
  ilustracion: ReactNode;
};

const juegos: Juego[] = [
  {
    numero: "01",
    titulo: "Conexiones",
    descripcion: "Agrupa 16 futbolistas en 4 grupos según lo que tienen en común. Ojo con las trampas.",
    etiquetas: ["Un puzzle por día", "1 jugador"],
    href: "/juegos/conexiones",
    fondo: "from-[#f5c518]/25 via-[#63c27c]/15 to-transparent",
    ilustracion: <MiniConexiones />,
  },
  {
    numero: "02",
    titulo: "Dato Falso",
    descripcion: "Duelo en una misma pantalla: cuatro datos son verdaderos y uno es falso. ¿Quién lo encuentra?",
    etiquetas: ["Duelo", "2 jugadores", "40 preguntas"],
    href: "/juegos/dato-falso",
    fondo: "from-[#d93a2b]/20 via-[#f5c518]/10 to-transparent",
    ilustracion: <MiniDatoFalso />,
  },
  {
    numero: "03",
    titulo: "Último en pie",
    descripcion:
      "Digan por turnos jugadores de la categoría. Si desconfías del rival, verifícalo: el que falla, pierde.",
    etiquetas: ["Duelo", "2 jugadores", "15 rondas"],
    href: "/juegos/ultimo-en-pie",
    fondo: "from-[#0e7a3e]/25 via-[#f5c518]/10 to-transparent",
    ilustracion: <MiniUltimoEnPie />,
  },
  {
    numero: "04",
    titulo: "Buscaminas",
    descripcion: "12 jugadores cumplen la categoría y 4 son impostores. Por turnos, el que toca un impostor pierde la ronda.",
    etiquetas: ["Duelo", "2 jugadores", "15 rondas"],
    href: "/juegos/buscaminas",
    fondo: "from-[#d93a2b]/15 via-[#0e7a3e]/15 to-transparent",
    ilustracion: <MiniBuscaminas />,
  },
  {
    numero: "05",
    titulo: "Mayor o menor",
    descripcion: "¿Más goles, asistencias, títulos, partidos o millones? Adivina si el siguiente tiene más o menos y sigue la racha.",
    etiquetas: ["1 a 4 jugadores", "5 categorías"],
    href: "/juegos/mayor-o-menor",
    fondo: "from-[#1d6fa5]/20 via-[#5aade6]/10 to-transparent",
    ilustracion: <MiniMayorMenor />,
  },
];

const formato = new Intl.NumberFormat("es");

export default async function Home() {
  const estadisticas = await leerEstadisticas();

  return (
    <main className="flex flex-1 flex-col">
      {/* ---------------------------------------------------------- Portada */}
      <section className="grano relative overflow-hidden bg-noche text-white">
        <div className="reflectores absolute inset-0" aria-hidden="true" />
        {/* Cancha en perspectiva; se desvanece hacia arriba sin cortes */}
        <div
          className="absolute inset-x-0 bottom-0 h-64 [perspective:900px] [mask-image:linear-gradient(to_top,black_15%,transparent_70%)] lg:h-96"
          aria-hidden="true"
        >
          <div className="cesped absolute inset-x-[-20%] bottom-[-55%] h-[180%] origin-bottom [transform:rotateX(62deg)]">
            <Cancha className="h-full w-full opacity-70" />
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-3xl px-4 pt-14 pb-40 text-center lg:max-w-6xl lg:px-8 lg:pt-24 lg:pb-56">
          <p className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium text-white/80 backdrop-blur lg:text-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-tarjeta shadow-[0_0_8px_var(--tarjeta)]" />
            Nuevo: Dato Falso, el duelo para dos
          </p>
          <h1 className="mt-5 font-display text-6xl leading-[0.9] font-extrabold uppercase drop-shadow-[0_4px_24px_rgba(0,0,0,0.35)] sm:text-7xl lg:text-[8.5rem]">
            Juegos
            <br className="lg:hidden" /> <span className="text-tarjeta">Futboleros</span>
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-base text-white/75 lg:mt-6 lg:text-xl">
            Pon a prueba cuánto sabes de fútbol latinoamericano y europeo. Reta a tus amigos con datos reales de
            jugadores, clubes y torneos.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link
              href="/juegos/conexiones"
              className="rounded-full bg-tarjeta px-6 py-3 font-display text-lg font-bold uppercase tracking-wide text-noche shadow-[0_8px_24px_-8px_rgba(245,197,24,0.7)] transition hover:-translate-y-0.5 hover:brightness-105 lg:px-8 lg:text-xl"
            >
              Jugar Conexiones
            </Link>
            <Link
              href="/juegos/dato-falso"
              className="rounded-full border border-white/25 bg-white/5 px-6 py-3 font-display text-lg font-bold uppercase tracking-wide text-white backdrop-blur transition hover:-translate-y-0.5 hover:bg-white/10 lg:px-8 lg:text-xl"
            >
              Retar a un amigo
            </Link>
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------- Marcador con datos reales */}
      {estadisticas && (
        <section className="relative z-10 mx-auto -mt-16 w-full max-w-3xl px-4 lg:-mt-20 lg:max-w-6xl lg:px-8">
          <div className="grid grid-cols-2 overflow-hidden rounded-3xl border border-white/10 bg-[#0b1f15] text-white shadow-[0_24px_60px_-20px_rgba(0,0,0,0.6)] lg:grid-cols-4">
            {[
              { n: estadisticas.jugadores, t: "jugadores" },
              { n: estadisticas.clubes, t: "clubes de 7 ligas" },
              { n: estadisticas.ediciones, t: "campeones de Champions, Mundial, Eurocopa y Copa América" },
              { n: estadisticas.titulos, t: "títulos y premios registrados" },
            ].map((x, i) => (
              <div
                key={x.t}
                className={`px-5 py-5 lg:px-8 lg:py-7 ${i % 2 === 1 ? "border-l border-white/10" : ""} ${
                  i >= 2 ? "border-t border-white/10 lg:border-t-0" : ""
                } ${i === 2 ? "lg:border-l" : ""}`}
              >
                <p className="digitos font-display text-4xl leading-none font-extrabold text-tarjeta lg:text-5xl">
                  {formato.format(x.n)}
                </p>
                <p className="mt-1.5 text-xs text-white/60 lg:text-sm">{x.t}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ---------------------------------------------------------- Juegos */}
      <section className="mx-auto w-full max-w-3xl px-4 pt-14 pb-16 lg:max-w-6xl lg:px-8 lg:pt-20 lg:pb-24">
        <p className="font-display text-sm font-bold uppercase tracking-[0.2em] text-cancha">Elige tu juego</p>
        <h2 className="mt-1 font-display text-4xl leading-none font-extrabold uppercase lg:text-5xl">A la cancha</h2>
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:gap-6">
          {juegos.map((juego) => (
            <TarjetaJuego key={juego.titulo} juego={juego} />
          ))}
        </div>
      </section>

      {/* ---------------------------------------------------------- Por qué es distinto */}
      <section className="puntos border-t border-borde">
        <div className="mx-auto grid w-full max-w-3xl gap-5 px-4 py-14 sm:grid-cols-3 lg:max-w-6xl lg:gap-8 lg:px-8 lg:py-20">
          <Caracteristica icono={<IconoVerificado />} titulo="Datos reales">
            Jugadores, clubes y títulos salen de Wikidata y Wikipedia, y cada pregunta se verifica antes de
            publicarse.
          </Caracteristica>
          <Caracteristica icono={<IconoAmigos />} titulo="Para jugar con amigos">
            Duelos en una misma pantalla, por turnos. Gana quien sume más puntos.
          </Caracteristica>
          <Caracteristica icono={<IconoActualizado />} titulo="Siempre al día">
            Los datos se actualizan desde sus fuentes y se renuevan solos en la página.
          </Caracteristica>
        </div>
      </section>
    </main>
  );
}

function TarjetaJuego({ juego }: { juego: Juego }) {
  const disponible = Boolean(juego.href);
  const contenido = (
    <>
      <div className={`relative flex h-40 items-center justify-center overflow-hidden bg-gradient-to-br ${juego.fondo} lg:h-48`}>
        <div className="puntos absolute inset-0 opacity-60" aria-hidden="true" />
        <span
          className="absolute top-3 left-4 font-display text-5xl font-extrabold text-tinta/10 lg:text-6xl"
          aria-hidden="true"
        >
          {juego.numero}
        </span>
        <div className="relative transition-transform duration-300 group-hover:scale-105">{juego.ilustracion}</div>
      </div>
      <div className="flex flex-1 flex-col border-t border-borde p-5 lg:p-7">
        <ul className="flex flex-wrap gap-1.5">
          {juego.etiquetas.map((e) => (
            <li
              key={e}
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                disponible ? "bg-cancha/10 text-cancha" : "bg-superficie-2 text-tenue"
              }`}
            >
              {e}
            </li>
          ))}
        </ul>
        <h3 className="mt-3 font-display text-3xl leading-none font-extrabold uppercase lg:text-4xl">
          {juego.titulo}
        </h3>
        <p className="mt-2 flex-1 text-sm text-tenue lg:mt-3 lg:text-base">{juego.descripcion}</p>
        <div className="mt-6 flex items-center justify-between">
          {disponible ? (
            <span className="font-display text-lg font-bold uppercase tracking-wide text-cancha">Jugar ahora</span>
          ) : (
            <span className="font-display text-lg font-bold uppercase tracking-wide text-tenue">En preparación</span>
          )}
          <span
            className={`flex h-10 w-10 items-center justify-center rounded-full text-lg transition-transform duration-300 ${
              disponible
                ? "bg-cancha text-sobre-cancha group-hover:translate-x-1"
                : "border border-borde text-tenue"
            }`}
            aria-hidden="true"
          >
            {disponible ? "→" : <IconoReloj />}
          </span>
        </div>
      </div>
    </>
  );

  const clases =
    "sombra-tarjeta group flex flex-col overflow-hidden rounded-3xl border border-borde bg-superficie transition duration-300";

  return disponible && juego.href ? (
    <Link
      href={juego.href}
      className={`${clases} hover:-translate-y-1 hover:border-cancha/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cancha`}
    >
      {contenido}
    </Link>
  ) : (
    <article className={`${clases} opacity-80`}>{contenido}</article>
  );
}

function Caracteristica({ icono, titulo, children }: { icono: ReactNode; titulo: string; children: ReactNode }) {
  return (
    <div className="sombra-tarjeta rounded-3xl border border-borde bg-superficie p-6 lg:p-7">
      <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-noche text-tarjeta">{icono}</span>
      <h3 className="mt-4 font-display text-2xl leading-none font-extrabold uppercase">{titulo}</h3>
      <p className="mt-2 text-sm text-tenue lg:text-base">{children}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ Ilustraciones */

function MiniConexiones() {
  const colores = ["bg-grupo-1", "bg-grupo-2", "bg-grupo-3", "bg-grupo-4"];
  return (
    <div className="grid -rotate-3 grid-cols-4 gap-1.5 rounded-2xl bg-superficie/70 p-3 shadow-lg backdrop-blur" aria-hidden="true">
      {colores.map((color, fila) =>
        [0, 1, 2, 3].map((col) => (
          <span
            key={`${fila}-${col}`}
            className={`h-6 w-11 rounded-md ${
              fila === 0 ? color : fila === 1 && col === 2 ? "bg-tinta" : "border border-borde bg-superficie"
            }`}
          />
        )),
      )}
    </div>
  );
}

function MiniDatoFalso() {
  return (
    <div className="flex w-52 rotate-2 flex-col gap-1.5 rounded-2xl bg-superficie/70 p-3 shadow-lg backdrop-blur" aria-hidden="true">
      {[true, true, false, true].map((verdadera, i) => (
        <span
          key={i}
          className={`flex h-6 items-center justify-end rounded-md px-2 text-[10px] font-bold ${
            verdadera ? "border border-borde bg-superficie text-cancha" : "bg-roja text-white shadow-md"
          }`}
        >
          {verdadera ? "✓" : "FALSO"}
        </span>
      ))}
    </div>
  );
}

function MiniUltimoEnPie() {
  return (
    <div className="flex w-56 -rotate-2 flex-col gap-2 rounded-2xl bg-superficie/70 p-3 shadow-lg backdrop-blur" aria-hidden="true">
      <span className="rounded-lg bg-noche px-3 py-2 font-display text-xs font-bold uppercase tracking-wide text-tarjeta">
        La categoría es…
      </span>
      <span className="flex items-center gap-2 rounded-lg border border-borde bg-superficie px-3 py-1.5 text-[11px] text-tenue">
        <span className="h-3 w-3 rounded-full border-2 border-tenue" /> Verificar jugador…
      </span>
      <span className="flex gap-1.5">
        <span className="rounded-full bg-cancha px-2 py-0.5 text-[10px] font-bold text-white">✓ Cumple</span>
        <span className="rounded-full bg-roja px-2 py-0.5 text-[10px] font-bold text-white">✗ No cumple</span>
      </span>
    </div>
  );
}

function MiniBuscaminas() {
  const celdas = ["ok", "", "ok", "", "", "mina", "", "ok", "ok", "", "", "", "", "ok", "", ""];
  return (
    <div className="grid -rotate-2 grid-cols-4 gap-1.5 rounded-2xl bg-superficie/70 p-3 shadow-lg backdrop-blur" aria-hidden="true">
      {celdas.map((c, i) => (
        <span
          key={i}
          className={`flex h-7 w-9 items-center justify-center rounded-md text-xs ${
            c === "ok" ? "bg-cancha text-white" : c === "mina" ? "bg-roja" : "border border-borde bg-superficie"
          }`}
        >
          {c === "ok" ? "✓" : c === "mina" ? "💣" : ""}
        </span>
      ))}
    </div>
  );
}

function MiniMayorMenor() {
  return (
    <div className="flex items-center gap-3" aria-hidden="true">
      <span className="flex h-16 w-14 -rotate-3 items-center justify-center rounded-xl bg-superficie font-display text-3xl font-extrabold shadow-lg">
        87
      </span>
      <span className="flex flex-col gap-1.5">
        <span className="flex h-7 w-10 items-center justify-center rounded-lg bg-cancha text-lg text-sobre-cancha shadow">
          ▲
        </span>
        <span className="flex h-7 w-10 items-center justify-center rounded-lg bg-roja text-lg text-white shadow">▼</span>
      </span>
      <span className="flex h-16 w-14 rotate-3 items-center justify-center rounded-xl border-2 border-dashed border-tinta/20 bg-superficie/50 font-display text-3xl font-extrabold text-tenue">
        ?
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ Íconos */

function IconoReloj() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </svg>
  );
}

function IconoVerificado() {
  return (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M12 2l2.4 2.1 3.2-.3.9 3.1 2.8 1.6-1 3 1 3-2.8 1.6-.9 3.1-3.2-.3L12 22l-2.4-2.1-3.2.3-.9-3.1L2.7 15.5l1-3-1-3 2.8-1.6.9-3.1 3.2.3z" />
      <path d="M8.5 12.2l2.3 2.3 4.7-4.8" />
    </svg>
  );
}

function IconoAmigos() {
  return (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <circle cx="8" cy="8" r="3.2" />
      <circle cx="16.5" cy="9" r="2.6" />
      <path d="M2.5 19.5c.6-3.2 2.9-5 5.5-5s4.9 1.8 5.5 5" />
      <path d="M14 14.6c.8-.4 1.6-.6 2.5-.6 2.2 0 4.1 1.5 4.6 4.3" />
    </svg>
  );
}

function IconoActualizado() {
  return (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M20 11a8 8 0 0 0-14.3-4.9L4 8" />
      <path d="M4 3.5V8h4.5" />
      <path d="M4 13a8 8 0 0 0 14.3 4.9L20 16" />
      <path d="M20 20.5V16h-4.5" />
    </svg>
  );
}
