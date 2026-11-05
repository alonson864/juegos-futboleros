import type { FotoInfo } from "../../componentes/Foto";

export type Grupo = {
  categoria: string;
  dificultad: number;
  jugadores: string[];
  jugadores_qid?: string[];
  fotos?: (FotoInfo | null)[];
  clave?: string;
  revisar?: boolean;
};

export type Puzzle = {
  id: number;
  fecha: string;
  grupos: Grupo[];
  trampas: string[];
};
