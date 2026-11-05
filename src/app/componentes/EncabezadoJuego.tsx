import Link from "next/link";
import type { ReactNode } from "react";
import { Cancha } from "./Cancha";

/** Banda superior de cada juego, con el ambiente de estadio de la portada. */
export default function EncabezadoJuego({
  titulo,
  acento,
  descripcion,
  etiquetas,
}: {
  titulo: string;
  acento?: string;
  descripcion: ReactNode;
  etiquetas: string[];
}) {
  return (
    <section className="grano relative overflow-hidden bg-noche text-white">
      <div className="reflectores absolute inset-0" aria-hidden="true" />
      <Cancha className="absolute -right-24 -bottom-40 hidden h-[26rem] w-[40rem] opacity-25 [transform:perspective(900px)_rotateX(55deg)] lg:block" />
      <div className="relative mx-auto w-full max-w-md px-4 pt-6 pb-8 lg:max-w-5xl lg:px-8 lg:pt-8 lg:pb-12">
        <nav className="text-xs text-white/60 lg:text-sm" aria-label="Ruta">
          <Link href="/" className="hover:text-white">
            Inicio
          </Link>
          <span className="mx-2" aria-hidden="true">
            /
          </span>
          <span className="text-white/90">{acento ? `${titulo} ${acento}` : titulo}</span>
        </nav>
        <h1 className="mt-3 font-display text-4xl leading-none font-extrabold uppercase lg:mt-4 lg:text-7xl">
          {titulo} {acento && <span className="text-tarjeta">{acento}</span>}
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-white/75 lg:mt-4 lg:text-lg">{descripcion}</p>
        <ul className="mt-4 flex flex-wrap gap-2 lg:mt-6">
          {etiquetas.map((e) => (
            <li
              key={e}
              className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium text-white/85 backdrop-blur lg:text-sm"
            >
              {e}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
