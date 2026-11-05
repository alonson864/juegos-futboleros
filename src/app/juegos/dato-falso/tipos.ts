import type { FotoInfo } from "../../componentes/Foto";

export type Dificultad = "facil" | "intermedio" | "dificil";

export type Opcion = {
  texto: string;
  qid: string;
  verdadera: boolean;
  foto?: FotoInfo;
};

export type Pregunta = {
  id: number;
  tipo:
    | "clubes_de_jugador"
    | "jugadores_de_club"
    | "jugadores_de_pais"
    | "ganadores_de_titulo"
    | "equipos_campeones"
    | "titulos_de_jugador";
  dificultad: Dificultad;
  afirmacion: string;
  opciones: Opcion[];
  explicacion: string;
  protagonista?: { tipo: "jugador" | "club" | "pais" | "titulo"; qid: string; nombre: string; foto?: FotoInfo };
};
