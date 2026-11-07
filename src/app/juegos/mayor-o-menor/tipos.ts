import type { FotoInfo } from "../../componentes/Foto";

export type Categoria = "goles" | "asistencias" | "titulos" | "fichajes" | "partidos";

export type Item = {
  id: string;
  categoria: Categoria;
  jugador_qid: string;
  nombre: string;
  valor: number;
  detalle: string | null;
  foto?: FotoInfo | null;
};
