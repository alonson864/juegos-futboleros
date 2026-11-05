import { cacheLife, cacheTag } from "next/cache";
import { leerDeSupabase } from "@/lib/supabase";
import type { Categoria } from "./tipos";

type Fila = Omit<Categoria, "miembros_destacados"> & {
  miembros_destacados: (string | Categoria["miembros_destacados"][number])[];
};

/** Categorías de "Último en pie" guardadas en Supabase. Se refrescan cada hora. */
export async function leerCategorias(): Promise<Categoria[]> {
  "use cache";
  cacheLife("hours");
  cacheTag("ultimo-en-pie");
  const filas = await leerDeSupabase<Fila[]>(
    "ultimo_en_pie_categorias?select=id,titulo,dificultad,cantidad,miembros_destacados&order=id.asc",
  );
  // Acepta el formato anterior (solo nombres) y el nuevo (nombre + foto)
  return filas.map((c) => ({
    ...c,
    miembros_destacados: c.miembros_destacados.map((m) => (typeof m === "string" ? { nombre: m } : m)),
  }));
}
