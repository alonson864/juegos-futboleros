import Link from "next/link";
import type { ReactNode } from "react";

type Juego = {
  titulo: string;
  descripcion: string;
  href?: string;
  ilustracion: ReactNode;
};

const juegos: Juego[] = [
  {
    titulo: "Conexiones",
    descripcion:
      "Agrupa 16 futbolistas en 4 grupos según lo que tienen en común. Ojo con las trampas.",
    href: "/juegos/conexiones",
    ilustracion: <MiniConexiones />,
  },
  {
    titulo: "Dato Falso",
    descripcion:
      "Duelo para dos en una pantalla: cuatro datos son verdaderos y uno es falso. ¿Quién lo encuentra?",
    href: "/juegos/dato-falso",
    ilustracion: <MiniDatoFalso />,
  },
  {
    titulo: "Mayor o menor",
    descripcion:
      "¿Más goles, más partidos, más títulos? Adivina si el siguiente dato es mayor o menor.",
    ilustracion: <MiniMayorMenor />,
  },
];

export default function Home() {
  return (
    <main className="flex flex-1 flex-col">
      <section className="fondo-cancha px-4 pt-14 pb-10 text-center lg:pt-24 lg:pb-16">
        <p className="font-display text-sm font-bold uppercase tracking-[0.2em] text-cancha lg:text-base">
          Para jugar con amigos
        </p>
        <h1 className="mt-2 font-display text-5xl leading-none font-extrabold uppercase sm:text-6xl lg:text-8xl">
          Juegos
          <br className="lg:hidden" />{" "}
          <span className="text-cancha">Futboleros</span>
        </h1>
        <p className="mx-auto mt-4 max-w-sm text-base text-tenue lg:mt-6 lg:max-w-xl lg:text-xl">
          Pon a prueba cuánto sabes de fútbol latinoamericano y europeo.
        </p>
      </section>

      <section className="mx-auto grid w-full max-w-3xl gap-4 px-4 pb-14 sm:grid-cols-2 lg:max-w-6xl lg:grid-cols-3 lg:gap-6 lg:px-8 lg:pb-20">
        {juegos.map((juego) => (
          <TarjetaJuego key={juego.titulo} juego={juego} />
        ))}
      </section>
    </main>
  );
}

function TarjetaJuego({ juego }: { juego: Juego }) {
  const disponible = Boolean(juego.href);
  const contenido = (
    <>
      <div className="flex h-32 items-center justify-center bg-superficie-2 lg:h-44">
        {juego.ilustracion}
      </div>
      <div className="flex flex-1 flex-col p-5 lg:p-7">
        <h2 className="font-display text-3xl font-extrabold uppercase leading-none lg:text-4xl">
          {juego.titulo}
        </h2>
        <p className="mt-2 flex-1 text-sm text-tenue lg:mt-3 lg:text-base">{juego.descripcion}</p>
        {disponible ? (
          <span className="mt-5 inline-flex w-fit items-center gap-1 rounded-full bg-cancha px-5 py-2 font-display text-lg font-bold uppercase tracking-wide text-sobre-cancha transition-colors group-hover:bg-cancha-fuerte">
            Jugar <span aria-hidden="true">→</span>
          </span>
        ) : (
          <span className="mt-5 inline-flex w-fit items-center rounded-full border border-borde px-4 py-1.5 font-display text-base font-bold uppercase tracking-wide text-tenue">
            Próximamente
          </span>
        )}
      </div>
    </>
  );

  const clases =
    "group flex flex-col overflow-hidden rounded-3xl border border-borde bg-superficie shadow-sm";

  return disponible && juego.href ? (
    <Link
      href={juego.href}
      className={`${clases} transition hover:-translate-y-0.5 hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cancha`}
    >
      {contenido}
    </Link>
  ) : (
    <article className={`${clases} opacity-80`}>{contenido}</article>
  );
}

function MiniConexiones() {
  const colores = ["bg-grupo-1", "bg-grupo-2", "bg-grupo-3", "bg-grupo-4"];
  return (
    <div className="grid grid-cols-4 gap-1.5" aria-hidden="true">
      {colores.map((color, fila) =>
        [0, 1, 2, 3].map((col) => (
          <span
            key={`${fila}-${col}`}
            className={`h-5 w-9 rounded-md ${fila === 0 ? color : "bg-superficie"} ${
              fila === 0 ? "" : "border border-borde"
            }`}
          />
        )),
      )}
    </div>
  );
}

function MiniDatoFalso() {
  return (
    <div className="flex w-44 flex-col gap-1.5" aria-hidden="true">
      {[true, true, false, true].map((verdadera, i) => (
        <span
          key={i}
          className={`flex h-5 items-center justify-end rounded-md px-2 text-[10px] font-bold ${
            verdadera ? "border border-borde bg-superficie text-cancha" : "bg-roja text-white"
          }`}
        >
          {verdadera ? "✓" : "FALSO"}
        </span>
      ))}
    </div>
  );
}

function MiniMayorMenor() {
  return (
    <div className="flex items-center gap-3" aria-hidden="true">
      <span className="flex h-16 w-14 items-center justify-center rounded-xl bg-superficie font-display text-3xl font-extrabold shadow-sm">
        87
      </span>
      <span className="flex flex-col gap-1.5">
        <span className="flex h-7 w-10 items-center justify-center rounded-lg bg-cancha text-lg text-sobre-cancha">
          ▲
        </span>
        <span className="flex h-7 w-10 items-center justify-center rounded-lg bg-roja text-lg text-white">
          ▼
        </span>
      </span>
      <span className="flex h-16 w-14 items-center justify-center rounded-xl border-2 border-dashed border-borde font-display text-3xl font-extrabold text-tenue">
        ?
      </span>
    </div>
  );
}
