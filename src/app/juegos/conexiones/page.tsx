import type { Metadata } from "next";
import EncabezadoJuego from "../../componentes/EncabezadoJuego";
import Conexiones from "./Conexiones";
import { leerPuzzles } from "./datos";

export const metadata: Metadata = {
  title: "Conexiones | Juegos Futboleros",
  description: "Encuentra los cuatro grupos de cuatro futbolistas.",
};

export default async function PaginaConexiones() {
  const puzzles = await leerPuzzles();

  return (
    <main className="flex flex-1 flex-col">
      <EncabezadoJuego
        titulo="Conexiones"
        descripcion="Encuentra los 4 grupos de 4 futbolistas que tienen algo en común. Tienes 4 errores."
        etiquetas={["Un puzzle por día", "1 jugador", "4 errores permitidos"]}
      />
      <div className="puntos flex-1">
        <div className="mx-auto w-full max-w-md px-4 pt-2 pb-12 lg:max-w-3xl lg:px-8 lg:pt-6 lg:pb-20">
          <div className="lg:sombra-tarjeta lg:mt-4 lg:rounded-3xl lg:border lg:border-borde lg:bg-superficie lg:px-10 lg:pt-4 lg:pb-10">
            {puzzles.length > 0 ? (
              <Conexiones puzzles={puzzles} />
            ) : (
              <SinDatos texto="Todavía no hay puzzles disponibles." />
            )}
          </div>
        </div>
      </div>
    </main>
  );
}

function SinDatos({ texto }: { texto: string }) {
  return (
    <div className="mt-8 rounded-3xl border border-dashed border-borde bg-superficie/60 px-6 py-12 text-center">
      <p className="font-display text-2xl font-extrabold uppercase">Calentando motores</p>
      <p className="mt-2 text-tenue">{texto} Vuelve en un rato.</p>
    </div>
  );
}
