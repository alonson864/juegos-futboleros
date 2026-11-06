import type { FotoInfo } from "../../componentes/Foto";

export type Dificultad = "facil" | "intermedio" | "dificil";

export type Ficha = {
  qid: string;
  nombre: string;
  cumple: boolean;
  foto?: FotoInfo;
};

export type Ronda = {
  id: number;
  categoria: string;
  titulo: string;
  dificultad: Dificultad;
  fichas: Ficha[];
  explicacion: string;
};
