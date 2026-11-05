import type { Metadata } from "next";
import EncabezadoJuego from "../../componentes/EncabezadoJuego";
import DatoFalso from "./DatoFalso";
import { leerPreguntas } from "./datos";

export const metadata: Metadata = {
  title: "Dato Falso Futbolero | Juegos Futboleros",
  description: "Duelo para dos en una misma pantalla: encuentra el dato falso antes que tu amigo.",
};

export default async function PaginaDatoFalso() {
  const preguntas = await leerPreguntas();

  return (
    <main className="flex flex-1 flex-col">
      <EncabezadoJuego
        titulo="Dato Falso"
        acento="Futbolero"
        descripcion="Duelo para dos en una misma pantalla. Cuatro datos son verdaderos y uno es falso: encuéntralo antes que tu amigo."
        etiquetas={["2 jugadores", "20 rondas", "Fácil · Intermedio · Difícil"]}
      />
      <div className="puntos flex-1">
        <div className="mx-auto w-full max-w-md px-4 pt-2 pb-12 lg:max-w-5xl lg:px-8 lg:pt-6 lg:pb-20">
          <div className="lg:sombra-tarjeta lg:mt-4 lg:rounded-3xl lg:border lg:border-borde lg:bg-superficie lg:px-10 lg:pt-2 lg:pb-10">
            {preguntas.length > 0 ? (
              <DatoFalso preguntas={preguntas} />
            ) : (
              <div className="mt-8 rounded-3xl border border-dashed border-borde bg-superficie/60 px-6 py-12 text-center">
                <p className="font-display text-2xl font-extrabold uppercase">Calentando motores</p>
                <p className="mt-2 text-tenue">Todavía no hay preguntas disponibles. Vuelve en un rato.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
