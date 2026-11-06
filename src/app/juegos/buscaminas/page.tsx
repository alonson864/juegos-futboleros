import type { Metadata } from "next";
import EncabezadoJuego from "../../componentes/EncabezadoJuego";
import Buscaminas from "./Buscaminas";
import { leerRondas } from "./datos";

export const metadata: Metadata = {
  title: "Buscaminas | Juegos Futboleros",
  description: "12 jugadores cumplen la categoría y 4 son impostores. El que toca un impostor, pierde la ronda.",
};

export default async function PaginaBuscaminas() {
  const rondas = await leerRondas();

  return (
    <main className="flex flex-1 flex-col">
      <EncabezadoJuego
        titulo="Buscaminas"
        descripcion="De 16 jugadores, 12 cumplen la categoría y 4 son impostores. Por turnos, toquen a los que cumplen. El que toca un impostor, pierde la ronda."
        etiquetas={["2 jugadores", "15 rondas", "Fácil · Intermedio · Difícil"]}
      />
      <div className="puntos flex-1">
        <div className="mx-auto w-full max-w-md px-4 pt-2 pb-12 lg:max-w-6xl lg:px-8 lg:pt-6 lg:pb-20">
          <div className="lg:sombra-tarjeta lg:mt-4 lg:rounded-3xl lg:border lg:border-borde lg:bg-superficie lg:px-10 lg:pt-2 lg:pb-10">
            {rondas.length > 0 ? (
              <Buscaminas rondas={rondas} />
            ) : (
              <div className="mt-8 rounded-3xl border border-dashed border-borde bg-superficie/60 px-6 py-12 text-center">
                <p className="font-display text-2xl font-extrabold uppercase">Calentando motores</p>
                <p className="mt-2 text-tenue">Todavía no hay rondas disponibles. Vuelve en un rato.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
