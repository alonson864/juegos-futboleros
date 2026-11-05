"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ENLACES = [
  { href: "/", texto: "Inicio" },
  { href: "/juegos/conexiones", texto: "Conexiones" },
  { href: "/juegos/dato-falso", texto: "Dato Falso" },
];

export default function Navegacion() {
  const ruta = usePathname();
  return (
    <nav className="flex items-center gap-1 text-sm" aria-label="Juegos">
      {ENLACES.map((e) => {
        const activo = e.href === "/" ? ruta === "/" : ruta.startsWith(e.href);
        return (
          <Link
            key={e.href}
            href={e.href}
            aria-current={activo ? "page" : undefined}
            className={`rounded-full px-3 py-1.5 font-medium transition-colors ${
              activo ? "bg-white/15 text-white" : "text-white/70 hover:bg-white/10 hover:text-white"
            } ${e.href === "/" ? "hidden sm:inline-block" : ""}`}
          >
            {e.texto}
          </Link>
        );
      })}
      <span className="ml-1 hidden items-center gap-1.5 rounded-full px-3 py-1.5 text-white/40 lg:inline-flex">
        Mayor o menor
        <span className="rounded-full bg-white/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide">
          Pronto
        </span>
      </span>
    </nav>
  );
}
