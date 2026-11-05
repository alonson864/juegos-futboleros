import type { Metadata } from "next";
import Link from "next/link";
import DatoFalso from "./DatoFalso";
import { leerPreguntas } from "./datos";

export const metadata: Metadata = {
  title: "Dato Falso Futbolero | Juegos Futboleros",
  description: "Duelo para dos en una misma pantalla: encuentra el dato falso antes que tu amigo.",
};

export default async function PaginaDatoFalso() {
  const preguntas = await leerPreguntas();

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col px-4 py-6 lg:max-w-5xl lg:px-8 lg:py-10">
      <Link href="/" className="text-sm font-medium text-cancha hover:underline">
        ← Todos los juegos
      </Link>
      <h1 className="mt-3 font-display text-4xl leading-none font-extrabold uppercase lg:text-6xl">
        Dato Falso <span className="text-roja">Futbolero</span>
      </h1>
      <p className="mt-1.5 text-sm text-tenue lg:mt-3 lg:max-w-2xl lg:text-lg">
        Duelo para dos en una misma pantalla. Cuatro datos son verdaderos y uno es falso: encuéntralo antes que tu amigo.
      </p>
      {preguntas.length > 0 ? (
        <DatoFalso preguntas={preguntas} />
      ) : (
        <p className="mt-10 text-center text-tenue">Todavía no hay preguntas disponibles.</p>
      )}
    </main>
  );
}
