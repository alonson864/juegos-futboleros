import type { Metadata } from "next";
import EncabezadoJuego from "../../componentes/EncabezadoJuego";
import MayorOMenor from "./MayorOMenor";
import { leerItems } from "./datos";

export const metadata: Metadata = {
  title: "Mayor o menor | Juegos Futboleros",
  description: "¿Más o menos goles, asistencias, títulos, partidos o millones? Adivina y sigue la racha.",
};

export default async function PaginaMayorOMenor() {
  const items = await leerItems();

  return (
    <main className="flex flex-1 flex-col">
      <EncabezadoJuego
        titulo="Mayor o menor"
        descripcion="Aparecen dos jugadores. Adivina si el de la derecha tiene más o menos que el de la izquierda. Cada acierto suma un punto; si fallas, sigue el próximo jugador desde ahí."
        etiquetas={["1 a 4 jugadores", "5 categorías", "10 jugadores por categoría"]}
      />
      <div className="puntos flex-1">
        <div className="mx-auto w-full max-w-md px-4 pt-2 pb-12 lg:max-w-6xl lg:px-8 lg:pt-6 lg:pb-20">
          <div className="lg:sombra-tarjeta lg:mt-4 lg:rounded-3xl lg:border lg:border-borde lg:bg-superficie lg:px-10 lg:pt-2 lg:pb-10">
            {items.length > 0 ? (
              <MayorOMenor items={items} />
            ) : (
              <div className="mt-8 rounded-3xl border border-dashed border-borde bg-superficie/60 px-6 py-12 text-center">
                <p className="font-display text-2xl font-extrabold uppercase">Calentando motores</p>
                <p className="mt-2 text-tenue">Todavía no hay jugadores disponibles. Vuelve en un rato.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
