export type Categoria = {
  id: number;
  titulo: string;
  dificultad: "facil" | "intermedio" | "dificil";
  cantidad: number;
  miembros_destacados: string[];
};

export type Resultado = {
  cumple: boolean | null;
  nombre: string;
  detalle: string;
  evidencia: { texto: string; detalle?: string; destacado: boolean }[];
};
