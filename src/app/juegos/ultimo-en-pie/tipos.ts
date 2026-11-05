import type { FotoInfo } from "../../componentes/Foto";

export type Categoria = {
  id: number;
  titulo: string;
  dificultad: "facil" | "intermedio" | "dificil";
  cantidad: number;
  miembros_destacados: { nombre: string; foto?: FotoInfo }[];
};

export type Resultado = {
  cumple: boolean | null;
  nombre: string;
  detalle: string;
  evidencia: { texto: string; detalle?: string; destacado: boolean }[];
  foto?: FotoInfo;
};
