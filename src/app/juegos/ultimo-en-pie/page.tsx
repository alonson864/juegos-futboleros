import type { Metadata } from "next";
import EncabezadoJuego from "../../componentes/EncabezadoJuego";
import { leerCategorias } from "./datos";
import UltimoEnPie from "./UltimoEnPie";

export const metadata: Metadata = {
  title: "Último en pie | Juegos Futboleros",
  description: "Digan por turnos jugadores que cumplan la categoría. El que se queda sin respuesta, pierde.",
};

export default async function PaginaUltimoEnPie() {
  const categorias = await leerCategorias();

  return (
    <main className="flex flex-1 flex-col">
      <EncabezadoJuego
        titulo="Último"
        acento="en pie"
        descripcion="Por turnos, digan jugadores que cumplan la categoría. Pierde el que se queda sin nombres, repite o dice uno que no cumple… si el otro lo descubre."
        etiquetas={["2 jugadores", "15 rondas", "Buscador para verificar"]}
      />
      <div className="puntos flex-1">
        <div className="mx-auto w-full max-w-md px-4 pt-2 pb-12 lg:max-w-6xl lg:px-8 lg:pt-6 lg:pb-20">
          <div className="lg:sombra-tarjeta lg:mt-4 lg:rounded-3xl lg:border lg:border-borde lg:bg-superficie lg:px-10 lg:pt-2 lg:pb-10">
            {categorias.length > 0 ? (
              <UltimoEnPie categorias={categorias} />
            ) : (
              <div className="mt-8 rounded-3xl border border-dashed border-borde bg-superficie/60 px-6 py-12 text-center">
                <p className="font-display text-2xl font-extrabold uppercase">Calentando motores</p>
                <p className="mt-2 text-tenue">Todavía no hay categorías disponibles. Vuelve en un rato.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
