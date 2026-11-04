import type { Metadata } from "next";
import Link from "next/link";
import datos from "../../../../data/conexiones.json";
import Conexiones from "./Conexiones";
import type { Puzzle } from "./tipos";

export const metadata: Metadata = {
  title: "Conexiones | Juegos Futboleros",
  description: "Encuentra los cuatro grupos de cuatro futbolistas.",
};

export default function PaginaConexiones() {
  const puzzles: Puzzle[] = datos.puzzles;

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col px-4 py-6">
      <Link href="/" className="text-sm text-foreground/60 hover:text-foreground">
        ← Inicio
      </Link>
      <h1 className="mt-3 text-3xl font-bold">🔗 Conexiones</h1>
      <p className="mt-1 text-sm text-foreground/70">
        Encuentra los 4 grupos de 4 futbolistas que tienen algo en común.
      </p>
      <Conexiones puzzles={puzzles} />
    </main>
  );
}
