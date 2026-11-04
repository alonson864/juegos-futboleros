export type Grupo = {
  categoria: string;
  dificultad: number;
  jugadores: string[];
  revisar?: boolean;
};

export type Puzzle = {
  id: number;
  fecha: string;
  grupos: Grupo[];
  trampas: string[];
};
