"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ENLACES = [
  { href: "/", texto: "Inicio" },
  { href: "/juegos/conexiones", texto: "Conexiones" },
  { href: "/juegos/dato-falso", texto: "Dato Falso" },
  { href: "/juegos/ultimo-en-pie", texto: "Último en pie" },
  { href: "/juegos/buscaminas", texto: "Buscaminas" },
  { href: "/juegos/mayor-o-menor", texto: "Mayor o menor" },
];

export default function Navegacion() {
  const ruta = usePathname();
  return (
    <nav className="flex min-w-0 items-center gap-1 overflow-x-auto text-sm [scrollbar-width:none]" aria-label="Juegos">
      {ENLACES.map((e) => {
        const activo = e.href === "/" ? ruta === "/" : ruta.startsWith(e.href);
        return (
          <Link
            key={e.href}
            href={e.href}
            aria-current={activo ? "page" : undefined}
            className={`shrink-0 rounded-full px-3 py-1.5 font-medium whitespace-nowrap transition-colors ${
              activo ? "bg-white/15 text-white" : "text-white/70 hover:bg-white/10 hover:text-white"
            } ${e.href === "/" ? "hidden sm:inline-block" : ""}`}
          >
            {e.texto}
          </Link>
        );
      })}
    </nav>
  );
}
