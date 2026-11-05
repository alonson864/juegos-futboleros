import type { Metadata } from "next";
import Link from "next/link";
import Conexiones from "./Conexiones";
import { leerPuzzles } from "./datos";

export const metadata: Metadata = {
  title: "Conexiones | Juegos Futboleros",
  description: "Encuentra los cuatro grupos de cuatro futbolistas.",
};

export default async function PaginaConexiones() {
  const puzzles = await leerPuzzles();

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col px-4 py-6 lg:max-w-3xl lg:px-8 lg:py-10">
      <Link href="/" className="text-sm font-medium text-cancha hover:underline">
        ← Todos los juegos
      </Link>
      <h1 className="mt-3 font-display text-4xl leading-none font-extrabold uppercase lg:text-6xl">Conexiones</h1>
      <p className="mt-1.5 text-sm text-tenue lg:mt-3 lg:text-lg">
        Encuentra los 4 grupos de 4 futbolistas que tienen algo en común.
      </p>
      {puzzles.length > 0 ? (
        <Conexiones puzzles={puzzles} />
      ) : (
        <p className="mt-10 text-center text-tenue">Todavía no hay puzzles disponibles.</p>
      )}
    </main>
  );
}
